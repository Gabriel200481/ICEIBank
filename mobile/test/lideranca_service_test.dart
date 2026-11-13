import 'package:flutter_test/flutter_test.dart';
import 'package:iceibank_mobile/lideranca_service.dart';
import 'package:iceibank_mobile/models.dart';

import 'helpers.dart';

AgenciaLideranca on(int id, int? lider) => AgenciaLideranca(idAgencia: id, online: true, liderId: lider);
AgenciaLideranca off(int id) => AgenciaLideranca(idAgencia: id, online: false);

void main() {
  test('consenso: as tres concordam na lider 2', () async {
    final servico = LiderancaService(ApiFalsa());
    await servico.atualizar();
    expect(servico.liderAtual, 2);
    expect(servico.emEleicao, isFalse);
    expect(servico.historico.single.descricao, contains('2'));
  });

  test('failover visivel: lider 2 cai, eleicao em andamento, depois lider 1', () async {
    final api = ApiFalsa();
    final servico = LiderancaService(api);
    await servico.atualizar();

    // 1) A agencia 2 caiu; 0 e 1 ainda nao perceberam (ainda dizem "2").
    api.liderancas = {0: on(0, 2), 1: on(1, 2), 2: off(2)};
    await servico.atualizar();
    expect(servico.liderAtual, isNull);
    expect(servico.emEleicao, isTrue);

    // 2) 0 e 1 reelegeram a agencia 1.
    api.liderancas = {0: on(0, 1), 1: on(1, 1), 2: off(2)};
    await servico.atualizar();
    expect(servico.liderAtual, 1);
    expect(servico.agencias[2].online, isFalse);
    expect(servico.historico.map((m) => m.descricao), [
      contains('eleita'),
      contains('eleicao em andamento'),
      contains('e a lider'),
    ]);
  });

  test('lider antiga volta e retoma a lideranca', () async {
    final api = ApiFalsa();
    final servico = LiderancaService(api);
    api.liderancas = {0: on(0, 1), 1: on(1, 1), 2: off(2)};
    await servico.atualizar();
    expect(servico.liderAtual, 1);
    api.liderancas = {0: on(0, 2), 1: on(1, 2), 2: on(2, 2)};
    await servico.atualizar();
    expect(servico.liderAtual, 2);
    expect(servico.historico.first.descricao, contains('da agencia 1 para a agencia 2'));
  });

  test('todas fora do ar: sem lider e sem historico espurio', () async {
    final api = ApiFalsa()..liderancas = {0: off(0), 1: off(1), 2: off(2)};
    final servico = LiderancaService(api);
    await servico.atualizar();
    expect(servico.liderAtual, isNull);
    expect(servico.historico, isEmpty);
  });

  test('sem mudanca nao acrescenta ao historico', () async {
    final servico = LiderancaService(ApiFalsa());
    await servico.atualizar();
    await servico.atualizar();
    await servico.atualizar();
    expect(servico.historico, hasLength(1));
  });

  test('notifica os ouvintes a cada atualizacao', () async {
    final servico = LiderancaService(ApiFalsa());
    var n = 0;
    servico.addListener(() => n++);
    await servico.atualizar();
    await servico.atualizar();
    expect(n, 2);
  });
}
