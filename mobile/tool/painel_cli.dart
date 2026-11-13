// ignore_for_file: avoid_print
// Verificacao manual contra agencias REAIS (nao e teste automatizado):
// usa o mesmo ApiClient do app para fazer o fluxo bancario e acompanhar a
// lideranca por N segundos, imprimindo o que o painel do app mostraria.
//
//   dart run tool/painel_cli.dart [segundos]
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:iceibank_mobile/api_client.dart';

String hora() => DateTime.now().toIso8601String().substring(11, 19);

Future<void> main(List<String> args) async {
  final segundos = args.isNotEmpty ? int.parse(args.first) : 5;
  final api = ApiClient(cliente: http.Client());

  await api.login('aluno', 'senha123');
  print('[${hora()}] login ok (token obtido)');

  var conta = await api.abrirConta(0, 'Ana');
  print('[${hora()}] conta aberta: ${conta.nomeAluno} saldo=${conta.saldo} versao=${conta.versao}');
  conta = await api.depositar(0, 200);
  print('[${hora()}] deposito 200 -> saldo=${conta.saldo}');
  conta = await api.sacar(0, 50);
  print('[${hora()}] saque 50 -> saldo=${conta.saldo}');
  await api.abrirConta(3, 'Caio'); // conta 3 -> agencia 0 (mesma agencia)
  print('[${hora()}] transferencia: ${await api.transferir(0, 3, 30)}');
  conta = await api.consultarConta(0);
  print('[${hora()}] saldo conta 0 = ${conta.saldo}; conta 3 = ${(await api.consultarConta(3)).saldo}');
  final extrato = await api.extrato(0);
  print('[${hora()}] extrato conta 0: ${extrato.map((m) => '${m.descricao}(${m.valor})').join(' | ')}');

  print('--- painel de lideranca por $segundos s (1 leitura/s) ---');
  int? anterior;
  for (var i = 0; i < segundos; i++) {
    final leituras = [for (var a = 0; a < 3; a++) await api.lideranca(a)];
    final txt = leituras.map((l) => 'ag${l.idAgencia}:${l.online ? 'lider=${l.liderId}' : 'FORA'}').join('  ');
    final lider = leituras.where((l) => l.online && l.liderId != null).map((l) => l.liderId).toSet();
    final marca = lider.length == 1 && lider.first != anterior ? '   <== lider agora: ${lider.first}' : '';
    if (lider.length == 1) anterior = lider.first;
    print('[${hora()}] $txt$marca');
    await Future<void>.delayed(const Duration(seconds: 1));
  }
  exit(0);
}
