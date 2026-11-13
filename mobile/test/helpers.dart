import 'dart:async';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:iceibank_mobile/api_client.dart';
import 'package:iceibank_mobile/conectividade.dart';
import 'package:iceibank_mobile/models.dart';

/// ApiClient com comportamento programavel, sem rede.
class ApiFalsa extends ApiClient {
  ApiFalsa() : super(cliente: MockClient((_) async => http.Response('{}', 200)));

  Conta conta = const Conta(id: 0, nomeAluno: 'Ana', saldo: 100, versao: [1, 0, 0]);
  bool contaExiste = true;
  bool offline = false;
  String? loginErro;
  Map<int, AgenciaLideranca> liderancas = {
    0: const AgenciaLideranca(idAgencia: 0, online: true, liderId: 2),
    1: const AgenciaLideranca(idAgencia: 1, online: true, liderId: 2),
    2: const AgenciaLideranca(idAgencia: 2, online: true, liderId: 2),
  };
  final List<String> chamadas = [];

  @override
  Future<void> login(String usuario, String senha) async {
    chamadas.add('login');
    if (offline) throw SemConexaoException(0);
    if (loginErro != null) throw ApiException(401, loginErro!);
    token = 'tok';
  }

  @override
  Future<Conta> consultarConta(int id) async {
    if (offline) throw SemConexaoException(id % 3);
    if (!contaExiste) throw ApiException(404, 'Conta nao encontrada nesta agencia.');
    return conta;
  }

  @override
  Future<Conta> abrirConta(int id, String nome) async {
    chamadas.add('abrir:$id:$nome');
    contaExiste = true;
    conta = Conta(id: id, nomeAluno: nome, saldo: 0, versao: const [1, 0, 0]);
    return conta;
  }

  @override
  Future<Conta> depositar(int id, double valor) async {
    chamadas.add('depositar:$valor');
    if (offline) throw SemConexaoException(id % 3);
    conta = conta.copyWith(saldo: conta.saldo + valor);
    return conta;
  }

  @override
  Future<Conta> sacar(int id, double valor) async {
    chamadas.add('sacar:$valor');
    if (offline) throw SemConexaoException(id % 3);
    if (conta.saldo < valor) throw ApiException(400, 'Saldo insuficiente.');
    conta = conta.copyWith(saldo: conta.saldo - valor);
    return conta;
  }

  @override
  Future<String> transferir(int origem, int destino, double valor) async {
    chamadas.add('transferir:$origem>$destino:$valor');
    if (offline) throw SemConexaoException(origem % 3);
    conta = conta.copyWith(saldo: conta.saldo - valor);
    return 'Transferencia concluida.';
  }

  List<MovimentoExtrato> movimentos = const [
    MovimentoExtrato(descricao: 'Abertura de conta', valor: 100, horaParede: '2026-11-13T00:00:00+00:00'),
    MovimentoExtrato(descricao: 'Saque', valor: -30, horaParede: '2026-11-13T00:01:00+00:00'),
  ];

  @override
  Future<List<MovimentoExtrato>> extrato(int id) async {
    if (offline) throw SemConexaoException(id % 3);
    return movimentos;
  }

  @override
  Future<AgenciaLideranca> lideranca(int agencia) async => liderancas[agencia]!;
}

/// Servidor simulado com a mesma regra do backend (POST /sincronizar):
/// IGUAIS/DEPOIS aplica; ANTES/CONCORRENTES e conflito; idempotente por idOperacao.
class ServidorFalso extends ApiFalsa {
  final Set<String> aplicadas = {};
  bool perderProximaResposta = false;
  bool forcarRecusa400 = false;
  final List<List<int>> basesRecebidas = [];

  String _comparar(List<int> a, List<int> b) {
    final aMenor = List.generate(a.length, (i) => a[i] <= b[i]).every((x) => x);
    final bMenor = List.generate(a.length, (i) => b[i] <= a[i]).every((x) => x);
    if (aMenor && bMenor) return 'IGUAIS';
    if (aMenor) return 'ANTES';
    if (bMenor) return 'DEPOIS';
    return 'CONCORRENTES';
  }

  /// Outro dispositivo mexe na conta direto no servidor.
  void alteracaoExterna(double valor) {
    conta = conta.copyWith(saldo: conta.saldo + valor, versao: [conta.versao[0] + 1, conta.versao[1], conta.versao[2]]);
  }

  @override
  Future<SyncResultado> sincronizar({
    required String idOperacao,
    required String tipo,
    required int idConta,
    required double valor,
    required List<int> vetorBase,
  }) async {
    if (offline) throw SemConexaoException(0);
    basesRecebidas.add(vetorBase);
    if (aplicadas.contains(idOperacao)) return SyncResultado(SyncStatus.jaAplicada, conta);
    final relacao = _comparar(vetorBase, conta.versao);
    if (relacao == 'ANTES' || relacao == 'CONCORRENTES') return SyncResultado(SyncStatus.conflito, conta, relacao: relacao);
    if (forcarRecusa400) {
      forcarRecusa400 = false;
      throw ApiException(400, 'Saldo insuficiente.');
    }
    conta = conta.copyWith(
      saldo: conta.saldo + (tipo == 'DEPOSITO' ? valor : -valor),
      versao: [conta.versao[0] + 1, conta.versao[1], conta.versao[2]],
    );
    aplicadas.add(idOperacao);
    if (perderProximaResposta) {
      perderProximaResposta = false;
      throw SemConexaoException(0); // aplicou, mas a resposta nao chegou
    }
    return SyncResultado(SyncStatus.aplicada, conta);
  }
}

class RedeFalsa implements Conectividade {
  final controle = StreamController<bool>.broadcast();
  @override
  Stream<bool> get online => controle.stream;
}

