import 'package:flutter/material.dart';

import 'api_client.dart';
import 'conta_page.dart';
import 'lideranca_page.dart';
import 'lideranca_service.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.api, required this.idConta, this.lideranca});

  final ApiClient api;
  final int idConta;

  /// Injetavel para testes.
  final LiderancaService? lideranca;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late final LiderancaService _lideranca = widget.lideranca ?? LiderancaService(widget.api);
  int _aba = 0;

  @override
  void initState() {
    super.initState();
    // O painel de lideranca roda desde o login, para o historico de mudancas
    // nao perder uma troca que aconteca com outra aba aberta.
    _lideranca.iniciar();
  }

  @override
  void dispose() {
    _lideranca.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final paginas = [
      ContaPage(api: widget.api, idConta: widget.idConta),
      LiderancaPage(servico: _lideranca),
    ];
    return Scaffold(
      appBar: AppBar(title: Text('Conta ${widget.idConta}')),
      body: IndexedStack(index: _aba, children: paginas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _aba,
        onDestinationSelected: (i) => setState(() => _aba = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.account_balance_wallet_outlined), label: 'Conta'),
          NavigationDestination(icon: Icon(Icons.hub_outlined), label: 'Lideranca'),
        ],
      ),
    );
  }
}
