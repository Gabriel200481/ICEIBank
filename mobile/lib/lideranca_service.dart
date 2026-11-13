import 'dart:async';

import 'package:flutter/foundation.dart';

import 'api_client.dart';
import 'config.dart';
import 'models.dart';

class MudancaLideranca {
  MudancaLideranca(this.quando, this.descricao);

  final DateTime quando;
  final String descricao;
}

/// Consulta as 3 agencias periodicamente e mantem o painel de lideranca.
///
/// Pergunta a CADA agencia (nao so a uma): se a agencia usada pelo app cair,
/// o painel continua mostrando o que as outras sabem - e mostra quem caiu.
class LiderancaService extends ChangeNotifier {
  LiderancaService(this._api, {this.intervalo = const Duration(seconds: 2), DateTime Function()? agora})
      : _agora = agora ?? DateTime.now;

  final ApiClient _api;
  final Duration intervalo;
  final DateTime Function() _agora;
  Timer? _timer;

  List<AgenciaLideranca> agencias = const [];
  int? liderAtual;
  final List<MudancaLideranca> historico = [];
  bool _primeiraLeitura = true;

  /// Sem consenso: nenhuma agencia viva conhece um lider (eleicao em curso).
  bool get emEleicao => agencias.isNotEmpty && liderAtual == null;

  void iniciar() {
    atualizar();
    _timer ??= Timer.periodic(intervalo, (_) => atualizar());
  }

  void parar() {
    _timer?.cancel();
    _timer = null;
  }

  Future<void> atualizar() async {
    final leituras = await Future.wait([for (var i = 0; i < numeroAgencias; i++) _api.lideranca(i)]);
    final anterior = liderAtual;
    final novo = _consenso(leituras);

    agencias = leituras;
    liderAtual = novo;

    if (!_primeiraLeitura && novo != anterior) {
      final texto = novo == null
          ? 'Lider $anterior sem resposta - eleicao em andamento'
          : anterior == null
              ? 'Agencia $novo eleita lider'
              : 'Lideranca mudou da agencia $anterior para a agencia $novo';
      historico.insert(0, MudancaLideranca(_agora(), texto));
    } else if (_primeiraLeitura && novo != null) {
      historico.insert(0, MudancaLideranca(_agora(), 'Agencia $novo e a lider'));
    }
    if (agencias.any((a) => a.online)) _primeiraLeitura = false;
    notifyListeners();
  }

  /// Lider mais citado entre as agencias vivas que conhecem um lider.
  int? _consenso(List<AgenciaLideranca> leituras) {
    final votos = <int, int>{};
    for (final a in leituras.where((a) => a.online && a.liderId != null)) {
      votos[a.liderId!] = (votos[a.liderId!] ?? 0) + 1;
    }
    if (votos.isEmpty) return null;
    final lider = votos.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
    // Se o lider eleito esta fora do ar, o consenso ainda nao e confiavel:
    // as agencias vivas vao reeleger em instantes.
    final liderLeitura = leituras.where((a) => a.idAgencia == lider);
    if (liderLeitura.isNotEmpty && !liderLeitura.first.online) return null;
    return lider;
  }

  @override
  void dispose() {
    parar();
    super.dispose();
  }
}
