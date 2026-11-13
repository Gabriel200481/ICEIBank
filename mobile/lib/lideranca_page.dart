import 'package:flutter/material.dart';

import 'formatacao.dart';
import 'lideranca_service.dart';
import 'models.dart';

/// Painel de lideranca: atualiza sozinho (o servico faz polling), entao uma
/// queda real da lider aparece aqui sem o usuario fazer nada.
class LiderancaPage extends StatelessWidget {
  const LiderancaPage({super.key, required this.servico});

  final LiderancaService servico;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: servico,
      builder: (context, _) {
        final tema = Theme.of(context);
        final lider = servico.liderAtual;
        return ListView(padding: const EdgeInsets.all(16), children: [
          Card(
            color: lider == null ? tema.colorScheme.errorContainer : tema.colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(children: [
                const Text('Lider atual'),
                Text(
                  lider == null ? (servico.emEleicao ? 'Eleicao em andamento...' : 'Consultando...') : 'Agencia $lider',
                  key: const Key('lider-atual'),
                  style: tema.textTheme.headlineMedium,
                ),
              ]),
            ),
          ),
          const SizedBox(height: 8),
          for (final a in servico.agencias) _CartaoAgencia(a, ehLider: a.idAgencia == lider),
          const SizedBox(height: 16),
          Text('Mudancas observadas', style: tema.textTheme.titleMedium),
          if (servico.historico.isEmpty) const Padding(padding: EdgeInsets.only(top: 8), child: Text('Nenhuma ainda.')),
          for (final m in servico.historico)
            ListTile(dense: true, leading: const Icon(Icons.history, size: 18), title: Text(m.descricao), subtitle: Text(hora(m.quando))),
        ]);
      },
    );
  }
}

class _CartaoAgencia extends StatelessWidget {
  const _CartaoAgencia(this.agencia, {required this.ehLider});

  final AgenciaLideranca agencia;
  final bool ehLider;

  @override
  Widget build(BuildContext context) {
    final cor = agencia.online ? Colors.green : Colors.red;
    return Card(
      child: ListTile(
        key: Key('agencia-${agencia.idAgencia}'),
        leading: Icon(Icons.circle, color: cor, size: 14),
        title: Text('Agencia ${agencia.idAgencia}${ehLider ? '  (lider)' : ''}'),
        subtitle: Text(agencia.online ? 'No ar - lider conhecido: ${agencia.liderId ?? 'nenhum'}' : 'Fora do ar'),
        trailing: ehLider ? const Icon(Icons.star, color: Colors.amber) : null,
      ),
    );
  }
}
