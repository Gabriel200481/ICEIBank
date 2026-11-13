import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'api_client.dart';
import 'armazenamento.dart';
import 'conectividade.dart';
import 'login_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(IceibankApp(
    api: ApiClient(cliente: http.Client()),
    armazenamento: await ArmazenamentoPrefs.abrir(),
    conectividade: ConectividadePlus(),
  ));
}

class IceibankApp extends StatelessWidget {
  const IceibankApp({super.key, required this.api, this.armazenamento, this.conectividade});

  final ApiClient api;
  final ArmazenamentoLocal? armazenamento;
  final Conectividade? conectividade;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ICEIBank',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF0B5FFF), useMaterial3: true),
      home: LoginPage(api: api, armazenamento: armazenamento, conectividade: conectividade),
    );
  }
}
