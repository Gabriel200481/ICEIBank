import 'package:flutter_test/flutter_test.dart';
import 'package:iceibank_mobile/armazenamento.dart';
import 'package:iceibank_mobile/conta_repositorio.dart';
import 'package:iceibank_mobile/models.dart';
import 'package:iceibank_mobile/operacao_pendente.dart';

import 'helpers.dart';

Future<void> deixarTarefasRodarem() => Future<void>.delayed(const Duration(milliseconds: 10));

void main() {
  late ServidorFalso servidor;
  late ArmazenamentoMemoria disco;
  late ContaRepositorio repo;
  var n = 0;

  ContaRepositorio novoRepo() =>
      ContaRepositorio(api: servidor, armazenamento: disco, gerarId: () => 'op-${n++}', agora: () => DateTime(2026, 11, 13));

  setUp(() async {
    n = 0;
    servidor = ServidorFalso();
    disco = ArmazenamentoMemoria();
    repo = novoRepo();
    await repo.carregar(0);
  });

  test('carregar busca a conta do servidor e guarda localmente', () async {
    expect(repo.contaServidor!.saldo, 100);
    expect(disco.dados.keys, contains('iceibank.conta.0'));
  });

  test('sem rede o app abre com o ultimo estado guardado', () async {
    servidor.offline = true;
    final reaberto = novoRepo();
    await reaberto.carregar(0);
    expect(reaberto.contaServidor!.saldo, 100);
    expect(reaberto.online, isFalse);
  });

  test('sem rede e sem cache nao ha conta (nada a mostrar)', () async {
    servidor.offline = true;
    final novo = ContaRepositorio(api: servidor, armazenamento: ArmazenamentoMemoria());
    await novo.carregar(0);
    expect(novo.contaServidor, isNull);
  });

  test('UI otimista: deposito offline muda o saldo exibido na hora e fica pendente', () async {
    servidor.offline = true;
    await repo.depositar(50);
    expect(repo.saldoExibido, 150);
    expect(repo.quantidadePendente, 1);
    expect(servidor.conta.saldo, 100); // servidor nao viu nada
  });

  test('saque offline tambem e otimista', () async {
    servidor.offline = true;
    await repo.sacar(30);
    expect(repo.saldoExibido, 70);
  });

  test('saque maior que o saldo exibido e barrado localmente', () async {
    expect(repo.sacar(500), throwsA(isA<SaldoInsuficienteLocal>()));
  });

  test('a fila sobrevive a fechar e reabrir o app', () async {
    servidor.offline = true;
    await repo.depositar(50);
    final reaberto = novoRepo();
    await reaberto.carregar(0);
    expect(reaberto.quantidadePendente, 1);
    expect(reaberto.saldoExibido, 150);
  });

  test('ao voltar a rede a fila e enviada em ordem, sem conflito entre operacoes do proprio app', () async {
    servidor.offline = true;
    await repo.depositar(50);
    await repo.sacar(20);
    await repo.depositar(5);
    servidor.offline = false;
    await repo.sincronizar();
    expect(repo.pendentes, isEmpty);
    expect(servidor.conta.saldo, 135);
    expect(repo.contaServidor!.saldo, 135);
    expect(repo.saldoExibido, 135);
    // 1a usa a base original; as seguintes, a versao devolvida pela anterior.
    expect(servidor.basesRecebidas[0], [1, 0, 0]);
    expect(servidor.basesRecebidas[1], [2, 0, 0]);
    expect(servidor.basesRecebidas[2], [3, 0, 0]);
  });

  test('sincronizacao automatica ao reconectar (evento de conectividade)', () async {
    final rede = RedeFalsa();
    repo.iniciarAutoSync(rede, reenvio: const Duration(hours: 1));
    servidor.offline = true;
    await repo.depositar(50);
    servidor.offline = false;
    rede.controle.add(true);
    await deixarTarefasRodarem();
    expect(repo.pendentes, isEmpty);
    expect(servidor.conta.saldo, 150);
    repo.dispose();
  });

  test('reenvio periodico sincroniza mesmo sem evento de rede', () async {
    final rede = RedeFalsa();
    repo.iniciarAutoSync(rede, reenvio: const Duration(milliseconds: 20));
    servidor.offline = true;
    await repo.depositar(50);
    servidor.offline = false;
    await Future<void>.delayed(const Duration(milliseconds: 100));
    expect(repo.pendentes, isEmpty);
    repo.dispose();
  });

  test('CONFLITO: a operacao fica marcada, nao e aplicada e o estado do servidor e exibido', () async {
    servidor.offline = true;
    await repo.depositar(50); // criada vendo versao [1,0,0]
    servidor.alteracaoExterna(10); // outro dispositivo muda a conta: versao [2,0,0]
    servidor.offline = false;
    await repo.sincronizar();

    final op = repo.pendentes.single;
    expect(op.estado, EstadoOperacao.conflito);
    expect(op.mensagem, contains('Conflito'));
    expect(op.contaServidor!.saldo, 110);
    expect(servidor.conta.saldo, 110); // NAO aplicou os 50
    expect(repo.conflitos, hasLength(1));
    expect(repo.saldoExibido, 110); // a operacao em conflito nao entra no saldo
  });

  test('operacoes depois de um conflito ficam retidas ate o usuario decidir', () async {
    servidor.offline = true;
    await repo.depositar(50);
    await repo.depositar(7);
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await repo.sincronizar();
    expect(repo.pendentes.map((o) => o.estado), [EstadoOperacao.conflito, EstadoOperacao.pendente]);
    expect(servidor.conta.saldo, 110);
  });

  test('descartar o conflito libera a proxima, que tambem era baseada no estado antigo e entra em conflito', () async {
    servidor.offline = true;
    await repo.depositar(50);
    await repo.depositar(7);
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await repo.sincronizar();
    await repo.descartar(repo.conflitos.single.idOperacao);
    await deixarTarefasRodarem();
    // A segunda (7) tambem partiu da versao antiga: conflito legitimo, nao e engolido.
    expect(repo.pendentes, hasLength(1));
    expect(repo.pendentes.single.estado, EstadoOperacao.conflito);
    expect(servidor.conta.saldo, 110);
    // O usuario decide reenviar essa sobre o estado atual.
    await repo.reenviarSobreEstadoAtual(repo.conflitos.single.idOperacao);
    await deixarTarefasRodarem();
    expect(repo.pendentes, isEmpty);
    expect(servidor.conta.saldo, 117);
  });

  test('reenviar sobre o estado atual aplica a operacao com a nova base', () async {
    servidor.offline = true;
    await repo.depositar(50);
    servidor.alteracaoExterna(10);
    servidor.offline = false;
    await repo.sincronizar();
    await repo.reenviarSobreEstadoAtual(repo.conflitos.single.idOperacao);
    await deixarTarefasRodarem();
    expect(repo.pendentes, isEmpty);
    expect(servidor.conta.saldo, 160);
  });

  test('conflito CONCORRENTE tambem e detectado', () async {
    servidor.offline = true;
    await repo.depositar(50);
    // O servidor tem uma alteracao que o app nao viu E o app viu algo que o servidor nao tem.
    servidor.conta = servidor.conta.copyWith(versao: [2, 0, 0]);
    final op = repo.pendentes.single;
    repo.pendentes[0] = op.copyWith(vetorBase: [1, 0, 2]);
    servidor.offline = false;
    await repo.sincronizar();
    expect(repo.pendentes.single.estado, EstadoOperacao.conflito);
    expect(repo.pendentes.single.mensagem, contains('CONCORRENTES'));
  });

  test('resposta perdida: o reenvio e idempotente (nao aplica duas vezes)', () async {
    servidor.perderProximaResposta = true;
    await repo.depositar(50);
    await deixarTarefasRodarem();
    expect(servidor.conta.saldo, 150); // o servidor aplicou
    expect(repo.pendentes, hasLength(1)); // o app nao sabe: continua pendente
    await repo.sincronizar(); // reenvia a mesma idOperacao
    expect(repo.pendentes, isEmpty);
    expect(servidor.conta.saldo, 150); // nao aplicou de novo
  });

  test('recusa de regra de negocio (400) marca como rejeitada, com a mensagem', () async {
    servidor.forcarRecusa400 = true;
    servidor.offline = true;
    await repo.sacar(30);
    servidor.offline = false;
    await repo.sincronizar();
    expect(repo.pendentes.single.estado, EstadoOperacao.rejeitada);
    expect(repo.pendentes.single.mensagem, 'Saldo insuficiente.');
    expect(repo.saldoExibido, 100);
  });

  test('sincronizar nao roda em paralelo consigo mesmo', () async {
    servidor.offline = true;
    await repo.depositar(50);
    servidor.offline = false;
    await Future.wait([repo.sincronizar(), repo.sincronizar(), repo.sincronizar()]);
    expect(servidor.conta.saldo, 150);
    expect(servidor.aplicadas, hasLength(1));
  });

  test('OperacaoPendente faz round-trip em JSON', () {
    final op = OperacaoPendente(
      idOperacao: 'x',
      tipo: 'SAQUE',
      idConta: 1,
      valor: 2.5,
      vetorBase: const [1, 2, 3],
      criadaEm: DateTime.utc(2026, 11, 13),
      estado: EstadoOperacao.conflito,
      mensagem: 'm',
      contaServidor: const Conta(id: 1, nomeAluno: 'B', saldo: 9, versao: [1, 2, 3]),
    );
    final volta = OperacaoPendente.fromJson(op.toJson());
    expect(volta.estado, EstadoOperacao.conflito);
    expect(volta.contaServidor!.saldo, 9);
    expect(volta.efeitoNoSaldo, -2.5);
  });
}
