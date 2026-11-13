import 'package:flutter/material.dart';

import 'api_client.dart';
import 'home_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.api});

  final ApiClient api;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _usuario = TextEditingController(text: 'aluno');
  final _senha = TextEditingController();
  final _conta = TextEditingController(text: '0');
  String? _erro;
  bool _carregando = false;

  Future<void> _entrar() async {
    final idConta = int.tryParse(_conta.text.trim());
    if (idConta == null || idConta < 0) {
      setState(() => _erro = 'Informe um numero de conta valido.');
      return;
    }
    setState(() {
      _carregando = true;
      _erro = null;
    });
    try {
      await widget.api.login(_usuario.text.trim(), _senha.text);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => HomePage(api: widget.api, idConta: idConta)),
      );
    } on ApiException catch (e) {
      setState(() => _erro = e.status == 401 ? 'Usuario ou senha invalidos.' : e.mensagem);
    } on SemConexaoException {
      setState(() => _erro = 'Nenhuma agencia respondeu. Verifique se estao no ar.');
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: ListView(
              padding: const EdgeInsets.all(24),
              shrinkWrap: true,
              children: [
                Text('ICEIBank', style: Theme.of(context).textTheme.headlineLarge, textAlign: TextAlign.center),
                const SizedBox(height: 24),
                TextField(key: const Key('usuario'), controller: _usuario, decoration: const InputDecoration(labelText: 'Usuario')),
                TextField(
                  key: const Key('senha'),
                  controller: _senha,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Senha'),
                ),
                TextField(
                  key: const Key('conta'),
                  controller: _conta,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Numero da conta'),
                ),
                const SizedBox(height: 16),
                if (_erro != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(_erro!, key: const Key('erro-login'), style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ),
                FilledButton(
                  key: const Key('entrar'),
                  onPressed: _carregando ? null : _entrar,
                  child: _carregando ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Entrar'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
