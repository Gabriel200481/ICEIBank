import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iceibank_mobile/armazenamento.dart';
import 'package:iceibank_mobile/conta_page.dart';
import 'package:iceibank_mobile/conta_repositorio.dart';

import 'helpers.dart';

Future<(ServidorFalso, ContaRepositorio)> montar(WidgetTester tester) async {
  final servidor = ServidorFalso();
  var n = 0;
  final repo = ContaRepositorio(api: servidor, armazenamento: ArmazenamentoMemoria(), gerarId: () => 'op${n++}');
  await tester.pumpWidget(MaterialApp(home: Scaffold(body: ContaPage(api: servidor, repositorio: repo, idConta: 0))));
  await tester.pumpAndSettle();
  return (servidor, repo);
}

Future<void> operar(WidgetTester tester, String botao, String valor) async {
  await tester.tap(find.byKey(Key(botao)));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('campo-valor')), valor);
  await tester.tap(find.byKey(const Key('confirmar-valor')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('offline: saldo muda na hora, operacao aparece como Pendente e ha aviso de falta de conexao', (tester) async {
    final (servidor, repo) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '50');
    expect(find.text('R\$ 150,00'), findsOneWidget); // UI otimista
    expect(find.text('Pendente'), findsOneWidget);
    expect(find.byKey(const Key('banner-offline')), findsOneWidget);
    expect(find.byKey(const Key('aviso-pendente')), findsOneWidget);
    expect(servidor.conta.saldo, 100); // servidor ainda nao sabe
    expect(repo.quantidadePendente, 1);
  });

  testWidgets('offline: transferir fica desabilitado (so deposito e saque entram na fila)', (tester) async {
    final (servidor, _) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '5');
    final botao = tester.widget<OutlinedButton>(find.byKey(const Key('transferir')));
    expect(botao.onPressed, isNull);
  });

  testWidgets('ao reconectar e tocar em Sincronizar agora a pendencia some e o servidor aplica', (tester) async {
    final (servidor, repo) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '50');
    servidor.offline = false;
    await tester.tap(find.byKey(const Key('sincronizar')));
    await tester.pumpAndSettle();
    expect(find.text('Pendente'), findsNothing);
    expect(servidor.conta.saldo, 150);
    expect(find.text('R\$ 150,00'), findsOneWidget);
    expect(repo.pendentes, isEmpty);
  });

  testWidgets('CONFLITO (409) e mostrado ao usuario, com o estado do servidor e as duas saidas', (tester) async {
    final (servidor, repo) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '50');
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await tester.tap(find.byKey(const Key('sincronizar')));
    await tester.pumpAndSettle();

    expect(find.text('Conflito'), findsOneWidget);
    expect(find.textContaining('a conta mudou no servidor'), findsOneWidget);
    expect(find.textContaining('No servidor agora: saldo R\$ 110,00'), findsOneWidget);
    expect(find.text('Descartar minha operacao'), findsOneWidget);
    expect(find.text('Reenviar sobre o estado atual'), findsOneWidget);
    expect(find.text('R\$ 110,00'), findsWidgets); // saldo exibido = servidor (conflito nao entra)
    expect(servidor.conta.saldo, 110);
    expect(repo.conflitos, hasLength(1));
  });

  testWidgets('conflito: Reenviar sobre o estado atual aplica e limpa a tela', (tester) async {
    final (servidor, repo) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '50');
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await tester.tap(find.byKey(const Key('sincronizar')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('reenviar-${repo.conflitos.single.idOperacao}')));
    await tester.pumpAndSettle();
    expect(find.text('Conflito'), findsNothing);
    expect(servidor.conta.saldo, 160);
    expect(find.text('R\$ 160,00'), findsOneWidget);
  });

  testWidgets('conflito: Descartar remove a operacao e mantem o saldo do servidor', (tester) async {
    final (servidor, repo) = await montar(tester);
    servidor.offline = true;
    await operar(tester, 'depositar', '50');
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await tester.tap(find.byKey(const Key('sincronizar')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(Key('descartar-${repo.conflitos.single.idOperacao}')));
    await tester.pumpAndSettle();
    expect(find.text('Conflito'), findsNothing);
    expect(servidor.conta.saldo, 110);
    expect(find.text('R\$ 110,00'), findsOneWidget);
  });

  testWidgets('saque acima do saldo exibido e barrado com mensagem', (tester) async {
    await montar(tester);
    await operar(tester, 'sacar', '999');
    expect(find.text('Saldo insuficiente.'), findsOneWidget);
    expect(find.text('Pendente'), findsNothing);
  });
}
