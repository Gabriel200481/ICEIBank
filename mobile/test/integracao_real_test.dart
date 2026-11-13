// Integracao contra uma agencia REAL (porta 4000). So roda com ICEIBANK_REAL=1:
//   ICEIBANK_REAL=1 flutter test test/integracao_real_test.dart
// Imprime o passo a passo (usado como evidencia do Sprint 3).
// ignore_for_file: avoid_print
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:iceibank_mobile/api_client.dart';
import 'package:iceibank_mobile/armazenamento.dart';
import 'package:iceibank_mobile/conta_repositorio.dart';

/// Rede que podemos "desligar": simula modo aviao sem tocar no servidor.
class RedeChaveavel extends http.BaseClient {
  RedeChaveavel(this._real);

  final http.Client _real;
  bool ligada = true;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    if (!ligada) throw http.ClientException('modo aviao');
    return _real.send(request);
  }
}

void main() {
  final ativo = Platform.environment['ICEIBANK_REAL'] == '1';

  test('offline-first ponta a ponta contra a agencia 0 real', () async {
    HttpOverrides.global = null; // flutter test bloqueia HTTP real por padrao
    final rede = RedeChaveavel(http.Client());
    final app = ApiClient(cliente: rede, urls: ['http://localhost:4000', 'http://localhost:4001', 'http://localhost:4002']);
    final outroAparelho = ApiClient(cliente: http.Client(), urls: app.urls);
    await app.login('aluno', 'senha123');
    await outroAparelho.login('aluno', 'senha123');
    await outroAparelho.abrirConta(0, 'Ana');
    await outroAparelho.depositar(0, 100);

    final disco = ArmazenamentoMemoria();
    final repo = ContaRepositorio(api: app, armazenamento: disco);
    await repo.carregar(0);
    print('1. app online. saldo servidor=${repo.contaServidor!.saldo} versao=${repo.contaServidor!.versao}');

    rede.ligada = false;
    await repo.depositar(50);
    await repo.sacar(20);
    print('2. MODO AVIAO: deposito 50 + saque 20 feitos offline');
    print('   saldoExibido (otimista)=${repo.saldoExibido}  pendentes=${repo.quantidadePendente}  online=${repo.online}');
    print('   saldo REAL no servidor (outro aparelho)=${(await outroAparelho.consultarConta(0)).saldo}');
    print('   armazenamento local guardou: ${disco.dados.keys.toList()}');

    rede.ligada = true;
    await repo.sincronizar();
    final aposSync = await outroAparelho.consultarConta(0);
    print('3. REDE VOLTOU: sincronizacao automatica da fila');
    print('   pendentes=${repo.pendentes.length}  saldo servidor=${aposSync.saldo}  versao=${aposSync.versao}');
    expect(repo.pendentes, isEmpty);
    expect(aposSync.saldo, repo.saldoExibido);

    rede.ligada = false;
    await repo.depositar(1000);
    print('4. OFFLINE de novo: deposito 1000 (app viu versao ${repo.contaServidor!.versao})');
    await outroAparelho.depositar(0, 10);
    print('   enquanto isso OUTRO aparelho deposita 10 direto no servidor');
    rede.ligada = true;
    await repo.sincronizar();
    final op = repo.conflitos.single;
    print('5. REDE VOLTOU: servidor respondeu HTTP 409');
    print('   estado da operacao: ${op.estado.name}');
    print('   mensagem ao usuario: ${op.mensagem}');
    print('   servidor agora: saldo=${op.contaServidor!.saldo} versao=${op.contaServidor!.versao}');
    print('   saldoExibido=${repo.saldoExibido} (o deposito de 1000 em conflito NAO entra no saldo)');
    expect((await outroAparelho.consultarConta(0)).saldo, op.contaServidor!.saldo);

    await repo.reenviarSobreEstadoAtual(op.idOperacao);
    final fim = await outroAparelho.consultarConta(0);
    print('6. usuario escolheu "Reenviar sobre o estado atual": pendentes=${repo.pendentes.length} saldo servidor=${fim.saldo}');
    expect(repo.pendentes, isEmpty);
    expect(fim.saldo, 1140); // 100 + 50 - 20 + 10 + 1000
  }, skip: ativo ? false : 'defina ICEIBANK_REAL=1 com as agencias no ar');
}
