import 'package:flutter/material.dart';

import 'api_client.dart';
import 'formatacao.dart';
import 'models.dart';

/// Funcionalidade adicional (Sprint 3): extrato da conta, derivado do log de
/// eventos da agencia (GET /contas/{id}/extrato). Precisa de conexao.
class ExtratoPage extends StatefulWidget {
  const ExtratoPage({super.key, required this.api, required this.idConta});

  final ApiClient api;
  final int idConta;

  @override
  State<ExtratoPage> createState() => _ExtratoPageState();
}

class _ExtratoPageState extends State<ExtratoPage> {
  late Future<List<MovimentoExtrato>> _futuro = widget.api.extrato(widget.idConta);

  void _recarregar() {
    final novo = widget.api.extrato(widget.idConta);
    setState(() {
      _futuro = novo;
    });
  }

  String _dataHora(String iso) {
    final d = DateTime.tryParse(iso)?.toLocal();
    if (d == null) return iso;
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')} ${hora(d)}';
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<MovimentoExtrato>>(
      future: _futuro,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
        if (snap.hasError) {
          final e = snap.error;
          final msg = e is SemConexaoException ? 'Sem conexao: o extrato precisa da agencia no ar.' : e.toString();
          return Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(msg, key: const Key('extrato-erro')),
              TextButton(key: const Key('extrato-tentar'), onPressed: _recarregar, child: const Text('Tentar de novo')),
            ]),
          );
        }
        final movimentos = snap.data!.reversed.toList(); // mais recente primeiro
        if (movimentos.isEmpty) return const Center(child: Text('Nenhuma movimentacao.'));
        return RefreshIndicator(
          onRefresh: () async => _recarregar(),
          child: ListView.separated(
            itemCount: movimentos.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final m = movimentos[i];
              final entrada = m.valor >= 0;
              return ListTile(
                key: Key('mov-$i'),
                leading: Icon(entrada ? Icons.south_west : Icons.north_east, color: entrada ? Colors.green : Colors.red),
                title: Text(m.descricao),
                subtitle: Text(_dataHora(m.horaParede)),
                trailing: Text(dinheiro(m.valor), style: TextStyle(color: entrada ? Colors.green : Colors.red)),
              );
            },
          ),
        );
      },
    );
  }
}
