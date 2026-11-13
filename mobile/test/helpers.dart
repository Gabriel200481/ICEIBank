import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:iceibank_mobile/api_client.dart';
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

  @override
  Future<AgenciaLideranca> lideranca(int agencia) async => liderancas[agencia]!;
}
