import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iceibank_mobile/extrato_page.dart';

import 'helpers.dart';

Widget pagina(ApiFalsa api) => MaterialApp(home: Scaffold(body: ExtratoPage(api: api, idConta: 0)));

void main() {
  testWidgets('lista as movimentacoes, mais recente primeiro, com entradas e saidas', (tester) async {
    await tester.pumpWidget(pagina(ApiFalsa()));
    await tester.pumpAndSettle();
    expect(find.text('Abertura de conta'), findsOneWidget);
    expect(find.text('Saque'), findsOneWidget);
    expect(find.text('R\$ 100,00'), findsOneWidget);
    expect(find.text('-R\$ 30,00'), findsOneWidget);
    final topo = tester.getTopLeft(find.text('Saque')).dy;
    final base = tester.getTopLeft(find.text('Abertura de conta')).dy;
    expect(topo, lessThan(base));
  });

  testWidgets('sem movimentacao mostra mensagem', (tester) async {
    await tester.pumpWidget(pagina(ApiFalsa()..movimentos = const []));
    await tester.pumpAndSettle();
    expect(find.text('Nenhuma movimentacao.'), findsOneWidget);
  });

  testWidgets('sem conexao mostra erro e permite tentar de novo', (tester) async {
    final api = ApiFalsa()..offline = true;
    await tester.pumpWidget(pagina(api));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('extrato-erro')), findsOneWidget);
    api.offline = false;
    await tester.tap(find.byKey(const Key('extrato-tentar')));
    await tester.pumpAndSettle();
    expect(find.text('Abertura de conta'), findsOneWidget);
  });
}
