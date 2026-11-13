import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'api_client.dart';
import 'armazenamento.dart';
import 'conectividade.dart';
import 'models.dart';
import 'operacao_pendente.dart';

class SaldoInsuficienteLocal implements Exception {
  @override
  String toString() => 'Saldo insuficiente.';
}

/// Repositorio offline-first de UMA conta.
///
/// - Armazenamento local: ultimo estado conhecido da conta + fila de pendentes
///   (sobrevivem ao fechar o app).
/// - UI otimista: deposito/saque entram na fila e o saldo exibido ja muda
///   (saldoExibido = saldo do servidor + pendentes), com ou sem rede.
/// - Sincronizacao: a fila e enviada em ordem para POST /sincronizar; ao
///   reconectar o envio e automatico.
/// - Conflito (HTTP 409): a operacao NAO e descartada nem reaplicada sozinha;
///   fica marcada como `conflito` com o estado do servidor, e o usuario decide.
class ContaRepositorio extends ChangeNotifier {
  ContaRepositorio({
    required this.api,
    required this.armazenamento,
    String Function()? gerarId,
    DateTime Function()? agora,
  })  : _gerarId = gerarId ?? _idPadrao,
        _agora = agora ?? DateTime.now;

  final ApiClient api;
  final ArmazenamentoLocal armazenamento;
  final String Function() _gerarId;
  final DateTime Function() _agora;

  static int _contador = 0;
  static String _idPadrao() => '${DateTime.now().microsecondsSinceEpoch}-${_contador++}';

  int? _idConta;
  Conta? contaServidor;
  List<OperacaoPendente> pendentes = [];
  bool online = true;
  bool sincronizando = false;
  bool contaInexistente = false;
  String? erro;

  StreamSubscription<bool>? _assinaturaRede;
  Timer? _timerReenvio;

  String get _chave => 'iceibank.conta.$_idConta';

  /// Saldo que o usuario ve: servidor + operacoes ainda nao confirmadas.
  /// Conflitos e rejeitadas nao entram - nao vao ser aplicadas como estao.
  double get saldoExibido {
    final base = contaServidor?.saldo ?? 0;
    return base + pendentes.where((o) => o.estado == EstadoOperacao.pendente).fold(0.0, (s, o) => s + o.efeitoNoSaldo);
  }

  int get quantidadePendente => pendentes.where((o) => o.estado == EstadoOperacao.pendente).length;
  List<OperacaoPendente> get conflitos => pendentes.where((o) => o.estado == EstadoOperacao.conflito).toList();

  Future<void> carregar(int idConta) async {
    _idConta = idConta;
    // 1) Local primeiro: o app abre instantaneamente, mesmo sem rede.
    final salvo = await armazenamento.ler(_chave);
    if (salvo != null) {
      final json = jsonDecode(salvo) as Map<String, dynamic>;
      contaServidor = json['conta'] == null ? null : Conta.fromJson(json['conta'] as Map<String, dynamic>);
      pendentes = (json['pendentes'] as List).map((e) => OperacaoPendente.fromJson(e as Map<String, dynamic>)).toList();
      notifyListeners();
    }
    // 2) Depois tenta atualizar do servidor.
    await sincronizar();
    if (pendentes.every((o) => o.estado != EstadoOperacao.pendente)) await atualizar();
  }

  Future<void> atualizar() async {
    try {
      contaServidor = await api.consultarConta(_idConta!);
      online = true;
      erro = null;
      contaInexistente = false;
      await _persistir();
    } on SemConexaoException {
      online = false;
    } on ApiException catch (e) {
      online = true;
      contaInexistente = e.status == 404;
      erro = contaInexistente ? null : e.mensagem;
    }
    notifyListeners();
  }

  Future<void> abrirConta(String nome) async {
    try {
      contaServidor = await api.abrirConta(_idConta!, nome);
      contaInexistente = false;
      erro = null;
      await _persistir();
    } on ApiException catch (e) {
      erro = e.mensagem;
    } on SemConexaoException {
      online = false;
      erro = 'Sem conexao: nao foi possivel abrir a conta agora.';
    }
    notifyListeners();
  }

  Future<void> _persistir() => armazenamento.gravar(
        _chave,
        jsonEncode({'conta': contaServidor?.toJson(), 'pendentes': pendentes.map((o) => o.toJson()).toList()}),
      );

  Future<void> depositar(double valor) => _enfileirar('DEPOSITO', valor);

  Future<void> sacar(double valor) async {
    // Checagem local so para o caso obvio; a decisao final e do servidor.
    if (valor > saldoExibido) throw SaldoInsuficienteLocal();
    return _enfileirar('SAQUE', valor);
  }

  Future<void> _enfileirar(String tipo, double valor) async {
    final conta = contaServidor;
    if (conta == null) throw StateError('Conta ainda nao carregada.');
    pendentes = [
      ...pendentes,
      OperacaoPendente(
        idOperacao: _gerarId(),
        tipo: tipo,
        idConta: conta.id,
        valor: valor,
        vetorBase: conta.versao,
        criadaEm: _agora(),
      ),
    ];
    await _persistir();
    notifyListeners(); // UI otimista: o saldo ja mudou aqui
    unawaited(sincronizar());
  }

  Future<void>? _emAndamento;
  bool _repetir = false;

  /// Envia a fila em ordem. Nunca roda duas rodadas em paralelo: se for
  /// chamada durante uma rodada (ex.: o usuario enfileirou outra operacao no
  /// meio), espera a atual terminar e roda mais uma - nada fica esquecido.
  Future<void> sincronizar() {
    if (_idConta == null) return Future.value();
    if (_emAndamento != null) {
      _repetir = true;
      return _emAndamento!;
    }
    return _emAndamento = _rodadas().whenComplete(() => _emAndamento = null);
  }

  Future<void> _rodadas() async {
    do {
      _repetir = false;
      await _umaRodada();
    } while (_repetir);
  }

  /// Uma passada pela fila. Para no primeiro conflito (as operacoes seguintes
  /// partiram de um estado que ja nao vale) e na primeira falta de rede.
  Future<void> _umaRodada() async {
    sincronizando = true;
    notifyListeners();
    try {
      List<int>? versaoAtual;
      while (true) {
        final i = pendentes.indexWhere((o) => o.estado == EstadoOperacao.pendente);
        if (i < 0 || pendentes.any((o) => o.estado == EstadoOperacao.conflito)) break;
        final op = pendentes[i];
        try {
          // A 1a operacao usa a base com que foi criada; as seguintes, a
          // versao devolvida pela anterior (dependem dela causalmente).
          final r = await api.sincronizar(
            idOperacao: op.idOperacao,
            tipo: op.tipo,
            idConta: op.idConta,
            valor: op.valor,
            vetorBase: versaoAtual ?? op.vetorBase,
          );
          online = true;
          erro = null;
          if (r.status == SyncStatus.conflito) {
            pendentes[i] = op.copyWith(
                estado: EstadoOperacao.conflito,
                contaServidor: r.conta,
                mensagem: 'Conflito (${r.relacao ?? '?'}): a conta mudou no servidor desde que voce a viu.');
            contaServidor = r.conta;
            break;
          }
          pendentes.removeAt(i);
          contaServidor = r.conta;
          versaoAtual = r.conta.versao;
        } on SemConexaoException {
          online = false;
          break;
        } on ApiException catch (e) {
          if (e.status == 401) {
            erro = 'Sessao expirada. Entre novamente.';
            break;
          }
          pendentes[i] = op.copyWith(estado: EstadoOperacao.rejeitada, mensagem: e.mensagem);
        }
        await _persistir();
        notifyListeners();
      }
      await _persistir();
    } finally {
      sincronizando = false;
      notifyListeners();
    }
  }

  /// Conflito: o usuario aceita o estado do servidor e abre mao da operacao.
  Future<void> descartar(String idOperacao) async {
    pendentes = pendentes.where((o) => o.idOperacao != idOperacao).toList();
    await _persistir();
    notifyListeners();
    await sincronizar();
  }

  /// Conflito: o usuario quer a operacao mesmo assim, agora sobre o estado
  /// atual do servidor (a base passa a ser a versao que o servidor devolveu).
  Future<void> reenviarSobreEstadoAtual(String idOperacao) async {
    pendentes = [
      for (final o in pendentes)
        if (o.idOperacao == idOperacao && o.contaServidor != null)
          o.copyWith(estado: EstadoOperacao.pendente, vetorBase: o.contaServidor!.versao)
        else
          o,
    ];
    await _persistir();
    notifyListeners();
    await sincronizar();
  }

  /// Liga a sincronizacao automatica: ao voltar a rede e, enquanto houver
  /// pendentes, a cada `reenvio` (a rede pode estar "ligada" e a agencia fora).
  void iniciarAutoSync(Conectividade conectividade, {Duration reenvio = const Duration(seconds: 5)}) {
    _assinaturaRede?.cancel();
    _assinaturaRede = conectividade.online.listen((ligada) {
      online = ligada;
      notifyListeners();
      if (ligada) unawaited(sincronizar());
    });
    _timerReenvio?.cancel();
    _timerReenvio = Timer.periodic(reenvio, (_) {
      if (quantidadePendente > 0 && !sincronizando) unawaited(sincronizar());
    });
  }

  @override
  void dispose() {
    _assinaturaRede?.cancel();
    _timerReenvio?.cancel();
    super.dispose();
  }
}
