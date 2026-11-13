import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:iceibank_mobile/api_client.dart';

const urls = ['http://a0', 'http://a1', 'http://a2'];

const contaJson = {'id': 4, 'nomeAluno': 'Bia', 'saldo': 50, 'versao': [0, 3, 0]};

ApiClient clienteCom(Future<http.Response> Function(http.Request) h) =>
    ApiClient(cliente: MockClient(h), urls: urls, timeout: const Duration(milliseconds: 200));

http.Response json(Object corpo, [int status = 200]) =>
    http.Response(jsonEncode(corpo), status, headers: {'content-type': 'application/json'});

void main() {
  test('login guarda o token', () async {
    final api = clienteCom((_) async => json({'access_token': 'abc', 'token_type': 'bearer'}));
    await api.login('aluno', 'senha123');
    expect(api.token, 'abc');
  });

  test('login com senha errada vira ApiException 401', () async {
    final api = clienteCom((_) async => json({'detail': 'Usuario ou senha invalidos.'}, 401));
    expect(api.login('aluno', 'x'), throwsA(isA<ApiException>().having((e) => e.status, 'status', 401)));
  });

  test('login tenta a proxima agencia quando a primeira esta fora do ar', () async {
    final visitadas = <String>[];
    final api = clienteCom((req) async {
      visitadas.add(req.url.host);
      if (req.url.host == 'a0') throw http.ClientException('recusada');
      return json({'access_token': 'zzz'});
    });
    await api.login('aluno', 'senha123');
    expect(visitadas, ['a0', 'a1']);
    expect(api.token, 'zzz');
  });

  test('login com todas fora do ar lanca SemConexaoException', () async {
    final api = clienteCom((_) async => throw http.ClientException('x'));
    expect(api.login('a', 'b'), throwsA(isA<SemConexaoException>()));
  });

  test('conta N e consultada na agencia N % 3 com o token', () async {
    late http.Request visto;
    final api = clienteCom((req) async {
      visto = req;
      return json(contaJson);
    });
    api.token = 'tk';
    final conta = await api.consultarConta(4);
    expect(visto.url.host, 'a1'); // 4 % 3 == 1
    expect(visto.headers['Authorization'], 'Bearer tk');
    expect(conta.versao, [0, 3, 0]);
    expect(conta.saldo, 50.0);
  });

  test('erro 404 da agencia vira ApiException com a mensagem', () async {
    final api = clienteCom((_) async => json({'detail': 'Conta nao encontrada nesta agencia.'}, 404));
    expect(api.consultarConta(1), throwsA(isA<ApiException>().having((e) => e.mensagem, 'msg', contains('nao encontrada'))));
  });

  test('timeout vira SemConexaoException', () async {
    final api = clienteCom((_) => Completer<http.Response>().future);
    expect(api.consultarConta(1), throwsA(isA<SemConexaoException>()));
  });

  test('transferir envia origem, destino e valor para a agencia da origem', () async {
    late http.Request visto;
    final api = clienteCom((req) async {
      visto = req;
      return json({'mensagem': 'ok'});
    });
    await api.transferir(2, 3, 10);
    expect(visto.url.host, 'a2');
    expect(jsonDecode(visto.body), {'idOrigem': 2, 'idDestino': 3, 'valor': 10});
  });

  test('lideranca de agencia fora do ar devolve online=false (nao lanca)', () async {
    final api = clienteCom((_) async => throw http.ClientException('x'));
    final l = await api.lideranca(2);
    expect(l.online, isFalse);
    expect(l.liderId, isNull);
  });

  test('lideranca le o liderId', () async {
    final api = clienteCom((_) async => json({'liderId': 2, 'idAgencia': 0}));
    final l = await api.lideranca(0);
    expect(l.online, isTrue);
    expect(l.liderId, 2);
  });

  test('sincronizar 200 devolve aplicada', () async {
    final api = clienteCom((_) async => json({'status': 'APLICADA', 'conta': contaJson}));
    final r = await api.sincronizar(idOperacao: 'a', tipo: 'DEPOSITO', idConta: 4, valor: 5, vetorBase: [0, 2, 0]);
    expect(r.status, SyncStatus.aplicada);
  });

  test('sincronizar 409 devolve conflito com o estado do servidor (nao lanca)', () async {
    final api = clienteCom((_) async => json({'status': 'CONFLITO', 'relacao': 'ANTES', 'conta': contaJson}, 409));
    final r = await api.sincronizar(idOperacao: 'a', tipo: 'SAQUE', idConta: 4, valor: 5, vetorBase: [0, 1, 0]);
    expect(r.status, SyncStatus.conflito);
    expect(r.relacao, 'ANTES');
    expect(r.conta.saldo, 50.0);
  });

  test('sincronizar com saldo insuficiente (400) lanca ApiException', () async {
    final api = clienteCom((_) async => json({'detail': 'Saldo insuficiente.'}, 400));
    expect(api.sincronizar(idOperacao: 'a', tipo: 'SAQUE', idConta: 4, valor: 5, vetorBase: [0, 1, 0]),
        throwsA(isA<ApiException>().having((e) => e.status, 's', 400)));
  });
}
