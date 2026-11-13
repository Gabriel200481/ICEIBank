import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import 'api_client.dart';
import 'login_page.dart';

void main() {
  runApp(IceibankApp(api: ApiClient(cliente: http.Client())));
}

class IceibankApp extends StatelessWidget {
  const IceibankApp({super.key, required this.api});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ICEIBank',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF0B5FFF), useMaterial3: true),
      home: LoginPage(api: api),
    );
  }
}
