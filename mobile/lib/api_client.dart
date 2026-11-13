import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';
import 'models.dart';

/// A agencia respondeu com erro HTTP (401, 400, 404...).
class ApiException implements Exception {
  ApiException(this.status, this.mensagem);

  final int status;
  final String mensagem;

  @override
  String toString() => mensagem;
}

/// Nao foi possivel falar com a agencia (timeout, conexao recusada, sem rede).
class SemConexaoException implements Exception {
  SemConexaoException(this.agencia);

  final int agencia;

  @override
  String toString() => 'Agencia $agencia fora do alcance.';
}

enum SyncStatus { aplicada, jaAplicada, conflito }

class SyncResultado {
  const SyncResultado(this.status, this.conta, {this.relacao});

  final SyncStatus status;

  /// Estado atual da conta no servidor (em conflito, e o que o usuario precisa ver).
  final Conta conta;
  final String? relacao;
}

class ApiClient {
  ApiClient({required http.Client cliente, List<String>? urls, this.timeout = const Duration(seconds: 2)})
      : _http = cliente,
        urls = urls ?? urlsPadrao();

  final http.Client _http;
  final List<String> urls;
  final Duration timeout;
  String? token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<http.Response> _enviar(int agencia, String metodo, String caminho, [Map<String, dynamic>? corpo]) async {
    final uri = Uri.parse('${urls[agencia]}$caminho');
    try {
      final future = metodo == 'GET'
          ? _http.get(uri, headers: _headers)
          : _http.post(uri, headers: _headers, body: jsonEncode(corpo ?? {}));
      return await future.timeout(timeout);
    } on TimeoutException {
      throw SemConexaoException(agencia);
    } on http.ClientException {
      throw SemConexaoException(agencia);
    }
  }

  dynamic _corpo(http.Response r) => r.body.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));

  Map<String, dynamic> _ok(http.Response r) {
    final corpo = _corpo(r);
    if (r.statusCode >= 400) {
      final detail = corpo is Map ? corpo['detail'] : null;
      throw ApiException(r.statusCode, detail is String ? detail : 'Erro ${r.statusCode}');
    }
    return corpo as Map<String, dynamic>;
  }

  /// Login em qualquer agencia no ar: o JWT e valido nas tres (mesmo segredo).
  Future<void> login(String usuario, String senha) async {
    SemConexaoException? ultimo;
    for (var i = 0; i < urls.length; i++) {
      try {
        final r = await _enviar(i, 'POST', '/auth/login', {'usuario': usuario, 'senha': senha});
        token = _ok(r)['access_token'] as String;
        return;
      } on SemConexaoException catch (e) {
        ultimo = e;
      }
    }
    throw ultimo ?? SemConexaoException(0);
  }

  Future<Conta> consultarConta(int id) async =>
      Conta.fromJson(_ok(await _enviar(agenciaDaConta(id), 'GET', '/contas/$id')));

  Future<Conta> abrirConta(int id, String nome) async => Conta.fromJson(
      _ok(await _enviar(agenciaDaConta(id), 'POST', '/contas', {'id': id, 'nomeAluno': nome, 'saldoInicial': 0})));

  Future<Conta> depositar(int id, double valor) async => Conta.fromJson(
      _ok(await _enviar(agenciaDaConta(id), 'POST', '/contas/$id/depositar', {'valor': valor})));

  Future<Conta> sacar(int id, double valor) async =>
      Conta.fromJson(_ok(await _enviar(agenciaDaConta(id), 'POST', '/contas/$id/sacar', {'valor': valor})));

  /// Transferencia sempre online: o app nao a enfileira (ver README do app).
  Future<String> transferir(int origem, int destino, double valor) async {
    final corpo = _ok(await _enviar(
        agenciaDaConta(origem), 'POST', '/transferencias', {'idOrigem': origem, 'idDestino': destino, 'valor': valor}));
    return corpo['mensagem'] as String;
  }

  Future<List<MovimentoExtrato>> extrato(int id) async {
    final corpo = _ok(await _enviar(agenciaDaConta(id), 'GET', '/contas/$id/extrato'));
    return (corpo['movimentos'] as List).map((m) => MovimentoExtrato.fromJson(m as Map<String, dynamic>)).toList();
  }

  /// GET /bully/lider de UMA agencia (sem JWT - rota entre agencias).
  Future<AgenciaLideranca> lideranca(int agencia) async {
    try {
      final corpo = _ok(await _enviar(agencia, 'GET', '/bully/lider'));
      return AgenciaLideranca(idAgencia: agencia, online: true, liderId: (corpo['liderId'] as num?)?.toInt());
    } on SemConexaoException {
      return AgenciaLideranca(idAgencia: agencia, online: false);
    }
  }

  /// POST /sincronizar: 200 aplica, 409 e CONFLITO (nao e erro: e um resultado
  /// que o app precisa mostrar), outros codigos viram ApiException.
  Future<SyncResultado> sincronizar({
    required String idOperacao,
    required String tipo,
    required int idConta,
    required double valor,
    required List<int> vetorBase,
  }) async {
    final r = await _enviar(agenciaDaConta(idConta), 'POST', '/sincronizar', {
      'idOperacao': idOperacao,
      'tipo': tipo,
      'idConta': idConta,
      'valor': valor,
      'vetorBase': vetorBase,
    });
    if (r.statusCode == 409) {
      final corpo = _corpo(r) as Map<String, dynamic>;
      return SyncResultado(SyncStatus.conflito, Conta.fromJson(corpo['conta'] as Map<String, dynamic>),
          relacao: corpo['relacao'] as String?);
    }
    final corpo = _ok(r);
    final status = corpo['status'] == 'JA_APLICADA' ? SyncStatus.jaAplicada : SyncStatus.aplicada;
    return SyncResultado(status, Conta.fromJson(corpo['conta'] as Map<String, dynamic>));
  }
}
