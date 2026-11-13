import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:iceibank_mobile/armazenamento.dart';
import 'package:iceibank_mobile/conta_page.dart';
import 'package:iceibank_mobile/conta_repositorio.dart';
import 'package:iceibank_mobile/home_page.dart';
import 'package:iceibank_mobile/lideranca_page.dart';
import 'package:iceibank_mobile/lideranca_service.dart';
import 'package:iceibank_mobile/login_page.dart';
import 'package:iceibank_mobile/models.dart';

import 'helpers.dart';

Widget app(Widget home) => MaterialApp(home: Scaffold(body: home));

Widget contaPage(ApiFalsa api, [ContaRepositorio? repo]) =>
    app(ContaPage(api: api, repositorio: repo ?? ContaRepositorio(api: api, armazenamento: ArmazenamentoMemoria()), idConta: 0));

void main() {
  group('Login', () {
    testWidgets('login valido abre a tela principal', (tester) async {
      final api = ApiFalsa();
      await tester.pumpWidget(MaterialApp(home: LoginPage(api: api)));
      await tester.enterText(find.byKey(const Key('senha')), 'senha123');
      await tester.tap(find.byKey(const Key('entrar')));
      await tester.pumpAndSettle();
      expect(find.text('Conta 0'), findsOneWidget);
      expect(api.token, 'tok');
    });

    testWidgets('senha invalida mostra erro e permanece no login', (tester) async {
      final api = ApiFalsa()..loginErro = 'Usuario ou senha invalidos.';
      await tester.pumpWidget(MaterialApp(home: LoginPage(api: api)));
      await tester.tap(find.byKey(const Key('entrar')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('erro-login')), findsOneWidget);
      expect(find.text('Usuario ou senha invalidos.'), findsOneWidget);
    });

    testWidgets('agencias fora do ar mostra mensagem de conexao', (tester) async {
      final api = ApiFalsa()..offline = true;
      await tester.pumpWidget(MaterialApp(home: LoginPage(api: api)));
      await tester.tap(find.byKey(const Key('entrar')));
      await tester.pumpAndSettle();
      expect(find.textContaining('Nenhuma agencia respondeu'), findsOneWidget);
    });

    testWidgets('numero de conta invalido nao chama a API', (tester) async {
      final api = ApiFalsa();
      await tester.pumpWidget(MaterialApp(home: LoginPage(api: api)));
      await tester.enterText(find.byKey(const Key('conta')), 'abc');
      await tester.tap(find.byKey(const Key('entrar')));
      await tester.pump();
      expect(find.textContaining('numero de conta valido'), findsOneWidget);
      expect(api.chamadas, isEmpty);
    });
  });

  group('Conta (fluxo bancario)', () {
    testWidgets('mostra o saldo', (tester) async {
      await tester.pumpWidget(contaPage(ServidorFalso()));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('saldo')), findsOneWidget);
      expect(find.text('R\$ 100,00'), findsOneWidget);
    });

    testWidgets('deposito atualiza o saldo', (tester) async {
      await tester.pumpWidget(contaPage(ServidorFalso()));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('depositar')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('campo-valor')), '25,50');
      await tester.tap(find.byKey(const Key('confirmar-valor')));
      await tester.pumpAndSettle();
      expect(find.text('R\$ 125,50'), findsOneWidget);
    });

    testWidgets('saque atualiza o saldo', (tester) async {
      await tester.pumpWidget(contaPage(ServidorFalso()));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sacar')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('campo-valor')), '40');
      await tester.tap(find.byKey(const Key('confirmar-valor')));
      await tester.pumpAndSettle();
      expect(find.text('R\$ 60,00'), findsOneWidget);
    });

    testWidgets('saque maior que o saldo mostra o erro do servidor', (tester) async {
      await tester.pumpWidget(contaPage(ServidorFalso()));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('sacar')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('campo-valor')), '999');
      await tester.tap(find.byKey(const Key('confirmar-valor')));
      await tester.pumpAndSettle();
      expect(find.text('Saldo insuficiente.'), findsOneWidget);
      expect(find.text('R\$ 100,00'), findsOneWidget);
    });

    testWidgets('transferencia chama a API com origem, destino e valor', (tester) async {
      final api = ServidorFalso();
      await tester.pumpWidget(contaPage(api));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('transferir')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('campo-destino')), '4');
      await tester.enterText(find.byKey(const Key('campo-valor-transferencia')), '30');
      await tester.tap(find.byKey(const Key('confirmar-transferencia')));
      await tester.pumpAndSettle();
      expect(api.chamadas, contains('transferir:0>4:30.0'));
      expect(find.text('Transferencia concluida.'), findsOneWidget);
    });

    testWidgets('conta inexistente oferece abrir conta', (tester) async {
      final api = ServidorFalso()..contaExiste = false;
      await tester.pumpWidget(contaPage(api));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('abrir-conta')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('campo-nome')), 'Ana');
      await tester.tap(find.byKey(const Key('confirmar-abertura')));
      await tester.pumpAndSettle();
      expect(api.chamadas, contains('abrir:0:Ana'));
      expect(find.byKey(const Key('saldo')), findsOneWidget);
    });

    testWidgets('agencia fora do ar mostra erro de conexao', (tester) async {
      final api = ServidorFalso()..offline = true;
      await tester.pumpWidget(contaPage(api));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('erro')), findsOneWidget);
    });
  });

  group('Painel de lideranca', () {
    testWidgets('mostra a lider e as 3 agencias', (tester) async {
      final servico = LiderancaService(ApiFalsa());
      await servico.atualizar();
      await tester.pumpWidget(app(LiderancaPage(servico: servico)));
      expect(find.text('Agencia 2'), findsWidgets);
      expect(find.byKey(const Key('agencia-0')), findsOneWidget);
      expect(find.byKey(const Key('agencia-1')), findsOneWidget);
      expect(find.byKey(const Key('agencia-2')), findsOneWidget);
      expect(find.textContaining('(lider)'), findsOneWidget);
    });

    testWidgets('failover aparece na tela sem nenhuma acao do usuario', (tester) async {
      final api = ApiFalsa();
      final servico = LiderancaService(api, intervalo: const Duration(seconds: 2));
      await tester.pumpWidget(app(LiderancaPage(servico: servico)));
      servico.iniciar();
      await tester.pump();
      await tester.pump();
      expect(find.text('Agencia 2'), findsWidgets);

      // A lider cai; o timer do servico (polling) detecta sozinho.
      api.liderancas = {
        0: const AgenciaLideranca(idAgencia: 0, online: true, liderId: 2),
        1: const AgenciaLideranca(idAgencia: 1, online: true, liderId: 2),
        2: const AgenciaLideranca(idAgencia: 2, online: false),
      };
      await tester.pump(const Duration(seconds: 2));
      await tester.pump();
      expect(find.textContaining('Eleicao em andamento'), findsOneWidget);
      expect(find.text('Fora do ar'), findsOneWidget);

      // As agencias vivas reelegem a 1.
      api.liderancas = {
        0: const AgenciaLideranca(idAgencia: 0, online: true, liderId: 1),
        1: const AgenciaLideranca(idAgencia: 1, online: true, liderId: 1),
        2: const AgenciaLideranca(idAgencia: 2, online: false),
      };
      await tester.pump(const Duration(seconds: 2));
      await tester.pump();
      expect(find.text('Agencia 1'), findsWidgets);
      expect(find.textContaining('eleita'), findsOneWidget);

      servico.parar();
    });

    testWidgets('HomePage troca para a aba Lideranca', (tester) async {
      final api = ApiFalsa();
      final servico = LiderancaService(api);
      await tester.pumpWidget(MaterialApp(home: HomePage(api: api, idConta: 0, lideranca: servico)));
      await tester.pump();
      await tester.tap(find.text('Lideranca'));
      await tester.pump();
      expect(find.byKey(const Key('lider-atual')), findsOneWidget);
      servico.parar();
    });
  });
}
