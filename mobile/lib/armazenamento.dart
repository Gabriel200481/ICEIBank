import 'package:shared_preferences/shared_preferences.dart';

/// Armazenamento local chave-valor. Interface propria para o repositorio nao
/// depender de plugin nativo - os testes usam a versao em memoria.
abstract class ArmazenamentoLocal {
  Future<String?> ler(String chave);
  Future<void> gravar(String chave, String valor);
}

class ArmazenamentoMemoria implements ArmazenamentoLocal {
  final Map<String, String> dados = {};

  @override
  Future<String?> ler(String chave) async => dados[chave];

  @override
  Future<void> gravar(String chave, String valor) async => dados[chave] = valor;
}

/// Persiste em SharedPreferences (arquivo local do app): sobrevive a fechar e
/// reabrir o app, que e o que a fila de pendentes precisa.
class ArmazenamentoPrefs implements ArmazenamentoLocal {
  ArmazenamentoPrefs(this._prefs);

  final SharedPreferences _prefs;

  static Future<ArmazenamentoPrefs> abrir() async => ArmazenamentoPrefs(await SharedPreferences.getInstance());

  @override
  Future<String?> ler(String chave) async => _prefs.getString(chave);

  @override
  Future<void> gravar(String chave, String valor) async {
    await _prefs.setString(chave, valor);
  }
}
