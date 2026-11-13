import 'package:flutter/material.dart';

import 'api_client.dart';
import 'formatacao.dart';
import 'models.dart';

class ContaPage extends StatefulWidget {
  const ContaPage({super.key, required this.api, required this.idConta});

  final ApiClient api;
  final int idConta;

  @override
  State<ContaPage> createState() => _ContaPageState();
}

class _ContaPageState extends State<ContaPage> {
  Conta? _conta;
  String? _erro;
  bool _naoExiste = false;
  bool _carregando = true;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() => _carregando = true);
    try {
      final conta = await widget.api.consultarConta(widget.idConta);
      setState(() {
        _conta = conta;
        _erro = null;
        _naoExiste = false;
      });
    } on ApiException catch (e) {
      setState(() {
        _naoExiste = e.status == 404;
        _erro = e.status == 404 ? null : e.mensagem;
      });
    } on SemConexaoException catch (e) {
      setState(() => _erro = e.toString());
    } finally {
      if (mounted) setState(() => _carregando = false);
    }
  }

  Future<void> _executar(Future<Conta> Function() acao) async {
    try {
      final conta = await acao();
      setState(() {
        _conta = conta;
        _erro = null;
      });
    } on ApiException catch (e) {
      setState(() => _erro = e.mensagem);
    } on SemConexaoException catch (e) {
      setState(() => _erro = e.toString());
    }
  }

  Future<double?> _pedirValor(String titulo) async {
    final controle = TextEditingController();
    final valor = await showDialog<double>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(titulo),
        content: TextField(
          key: const Key('campo-valor'),
          controller: controle,
          autofocus: true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(labelText: 'Valor (R\$)'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
          FilledButton(
            key: const Key('confirmar-valor'),
            onPressed: () => Navigator.pop(ctx, double.tryParse(controle.text.replaceAll(',', '.'))),
            child: const Text('Confirmar'),
          ),
        ],
      ),
    );
    if (valor == null || valor <= 0) return null;
    return valor;
  }

  Future<void> _transferir() async {
    final destinoCtl = TextEditingController();
    final valorCtl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Transferir'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(
              key: const Key('campo-destino'),
              controller: destinoCtl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Conta de destino')),
          TextField(
              key: const Key('campo-valor-transferencia'),
              controller: valorCtl,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Valor (R\$)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(key: const Key('confirmar-transferencia'), onPressed: () => Navigator.pop(ctx, true), child: const Text('Transferir')),
        ],
      ),
    );
    final destino = int.tryParse(destinoCtl.text.trim());
    final valor = double.tryParse(valorCtl.text.replaceAll(',', '.'));
    if (ok != true || destino == null || valor == null || valor <= 0) return;
    try {
      final mensagem = await widget.api.transferir(widget.idConta, destino, valor);
      await _carregar();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensagem)));
    } on ApiException catch (e) {
      setState(() => _erro = e.mensagem);
    } on SemConexaoException catch (e) {
      setState(() => _erro = e.toString());
    }
  }

  Future<void> _abrirConta() async {
    final nomeCtl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Abrir conta ${widget.idConta}'),
        content: TextField(key: const Key('campo-nome'), controller: nomeCtl, decoration: const InputDecoration(labelText: 'Nome do titular')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(key: const Key('confirmar-abertura'), onPressed: () => Navigator.pop(ctx, true), child: const Text('Abrir')),
        ],
      ),
    );
    if (ok != true || nomeCtl.text.trim().isEmpty) return;
    await _executar(() => widget.api.abrirConta(widget.idConta, nomeCtl.text.trim()));
    setState(() => _naoExiste = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_carregando && _conta == null) return const Center(child: CircularProgressIndicator());

    if (_naoExiste) {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('A conta ${widget.idConta} ainda nao existe.'),
          const SizedBox(height: 12),
          FilledButton(key: const Key('abrir-conta'), onPressed: _abrirConta, child: const Text('Abrir conta')),
        ]),
      );
    }

    final conta = _conta;
    return RefreshIndicator(
      onRefresh: _carregar,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        if (conta != null) ...[
          Text(conta.nomeAluno, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(dinheiro(conta.saldo), key: const Key('saldo'), style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: 16),
          Wrap(spacing: 8, children: [
            FilledButton.icon(
              key: const Key('depositar'),
              icon: const Icon(Icons.add),
              label: const Text('Depositar'),
              onPressed: () async {
                final v = await _pedirValor('Depositar');
                if (v != null) await _executar(() => widget.api.depositar(widget.idConta, v));
              },
            ),
            FilledButton.tonalIcon(
              key: const Key('sacar'),
              icon: const Icon(Icons.remove),
              label: const Text('Sacar'),
              onPressed: () async {
                final v = await _pedirValor('Sacar');
                if (v != null) await _executar(() => widget.api.sacar(widget.idConta, v));
              },
            ),
            OutlinedButton.icon(key: const Key('transferir'), icon: const Icon(Icons.swap_horiz), label: const Text('Transferir'), onPressed: _transferir),
          ]),
        ],
        if (_erro != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(_erro!, key: const Key('erro'), style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
      ]),
    );
  }
}
