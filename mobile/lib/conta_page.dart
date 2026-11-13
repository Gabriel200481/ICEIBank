import 'package:flutter/material.dart';

import 'api_client.dart';
import 'conta_repositorio.dart';
import 'formatacao.dart';
import 'operacao_pendente.dart';

/// Tela da conta, offline-first: deposito e saque passam pelo repositorio
/// (fila local + UI otimista); transferencia continua exigindo conexao.
class ContaPage extends StatefulWidget {
  const ContaPage({super.key, required this.api, required this.repositorio, required this.idConta});

  final ApiClient api;
  final ContaRepositorio repositorio;
  final int idConta;

  @override
  State<ContaPage> createState() => _ContaPageState();
}

class _ContaPageState extends State<ContaPage> {
  String? _erro;

  ContaRepositorio get repo => widget.repositorio;

  @override
  void initState() {
    super.initState();
    repo.carregar(widget.idConta);
  }

  Future<void> _executar(Future<void> Function() acao) async {
    try {
      await acao();
      if (mounted) setState(() => _erro = null);
    } on SaldoInsuficienteLocal catch (e) {
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
      await repo.atualizar();
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
    await repo.abrirConta(nomeCtl.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: repo,
      builder: (context, _) {
        if (repo.contaInexistente) {
          return Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('A conta ${widget.idConta} ainda nao existe.'),
              const SizedBox(height: 12),
              FilledButton(key: const Key('abrir-conta'), onPressed: _abrirConta, child: const Text('Abrir conta')),
            ]),
          );
        }

        final conta = repo.contaServidor;
        if (conta == null) {
          // Sem cache local e sem servidor: nao ha o que mostrar.
          return Center(
            child: repo.erro != null || !repo.online
                ? Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(repo.erro ?? 'Sem conexao e sem dados salvos neste aparelho.', key: const Key('erro')),
                  )
                : const CircularProgressIndicator(),
          );
        }

        final tema = Theme.of(context);
        final erro = _erro ?? repo.erro;
        return RefreshIndicator(
          onRefresh: () async {
            await repo.sincronizar();
            await repo.atualizar();
          },
          child: ListView(padding: const EdgeInsets.all(16), children: [
            if (!repo.online)
              Card(
                key: const Key('banner-offline'),
                color: tema.colorScheme.tertiaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    'Sem conexao. ${repo.quantidadePendente} operacao(oes) aguardando envio; '
                    'serao sincronizadas ao reconectar.',
                  ),
                ),
              ),
            Text(conta.nomeAluno, style: tema.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(dinheiro(repo.saldoExibido), key: const Key('saldo'), style: tema.textTheme.displaySmall),
            if (repo.quantidadePendente > 0)
              Text('Inclui ${repo.quantidadePendente} operacao(oes) ainda nao confirmada(s) pelo servidor',
                  key: const Key('aviso-pendente'), style: tema.textTheme.bodySmall),
            const SizedBox(height: 16),
            Wrap(spacing: 8, children: [
              FilledButton.icon(
                key: const Key('depositar'),
                icon: const Icon(Icons.add),
                label: const Text('Depositar'),
                onPressed: () async {
                  final v = await _pedirValor('Depositar');
                  if (v != null) await _executar(() => repo.depositar(v));
                },
              ),
              FilledButton.tonalIcon(
                key: const Key('sacar'),
                icon: const Icon(Icons.remove),
                label: const Text('Sacar'),
                onPressed: () async {
                  final v = await _pedirValor('Sacar');
                  if (v != null) await _executar(() => repo.sacar(v));
                },
              ),
              OutlinedButton.icon(
                key: const Key('transferir'),
                icon: const Icon(Icons.swap_horiz),
                label: const Text('Transferir'),
                // Transferencia entre contas nao e enfileirada: exige conexao.
                onPressed: repo.online ? _transferir : null,
              ),
              if (repo.pendentes.isNotEmpty)
                TextButton.icon(
                  key: const Key('sincronizar'),
                  icon: repo.sincronizando
                      ? const SizedBox(height: 14, width: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.sync),
                  label: const Text('Sincronizar agora'),
                  onPressed: repo.sincronizando ? null : repo.sincronizar,
                ),
            ]),
            if (erro != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(erro, key: const Key('erro'), style: TextStyle(color: tema.colorScheme.error)),
              ),
            if (repo.pendentes.isNotEmpty) ...[
              const SizedBox(height: 20),
              Text('Operacoes nao sincronizadas', style: tema.textTheme.titleMedium),
              for (final op in repo.pendentes) _CartaoOperacao(op: op, repo: repo),
            ],
          ]),
        );
      },
    );
  }
}

class _CartaoOperacao extends StatelessWidget {
  const _CartaoOperacao({required this.op, required this.repo});

  final OperacaoPendente op;
  final ContaRepositorio repo;

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    final (rotulo, cor) = switch (op.estado) {
      EstadoOperacao.pendente => ('Pendente', tema.colorScheme.secondaryContainer),
      EstadoOperacao.conflito => ('Conflito', tema.colorScheme.errorContainer),
      EstadoOperacao.rejeitada => ('Rejeitada', tema.colorScheme.errorContainer),
    };
    return Card(
      key: Key('op-${op.idOperacao}'),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${op.tipo == 'DEPOSITO' ? 'Deposito' : 'Saque'} de ${dinheiro(op.valor)}')),
            Chip(label: Text(rotulo), backgroundColor: cor, visualDensity: VisualDensity.compact),
          ]),
          if (op.estado == EstadoOperacao.conflito) ...[
            const SizedBox(height: 4),
            Text(op.mensagem ?? 'Conflito de versao.', key: Key('conflito-msg-${op.idOperacao}')),
            if (op.contaServidor != null)
              Text('No servidor agora: saldo ${dinheiro(op.contaServidor!.saldo)}  (versao ${op.contaServidor!.versao.join(',')})'),
            const SizedBox(height: 8),
            Wrap(spacing: 8, children: [
              OutlinedButton(
                key: Key('descartar-${op.idOperacao}'),
                onPressed: () => repo.descartar(op.idOperacao),
                child: const Text('Descartar minha operacao'),
              ),
              FilledButton(
                key: Key('reenviar-${op.idOperacao}'),
                onPressed: () => repo.reenviarSobreEstadoAtual(op.idOperacao),
                child: const Text('Reenviar sobre o estado atual'),
              ),
            ]),
          ],
          if (op.estado == EstadoOperacao.rejeitada) ...[
            const SizedBox(height: 4),
            Text(op.mensagem ?? 'Recusada pelo servidor.'),
            TextButton(
              key: Key('descartar-${op.idOperacao}'),
              onPressed: () => repo.descartar(op.idOperacao),
              child: const Text('Remover'),
            ),
          ],
        ]),
      ),
    );
  }
}
