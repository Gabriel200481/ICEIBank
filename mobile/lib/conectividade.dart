import 'package:connectivity_plus/connectivity_plus.dart';

/// Abstracao sobre "tem rede?" para o repositorio ser testavel sem plugin.
abstract class Conectividade {
  Stream<bool> get online;
}

class ConectividadePlus implements Conectividade {
  @override
  Stream<bool> get online =>
      Connectivity().onConnectivityChanged.map((r) => r.any((c) => c != ConnectivityResult.none));
}
