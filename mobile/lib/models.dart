/// Conta como a agencia a devolve. `versao` e o vetor da ultima alteracao
/// (relogio vetorial) - base da deteccao de conflito na sincronizacao.
class Conta {
  const Conta({required this.id, required this.nomeAluno, required this.saldo, required this.versao});

  final int id;
  final String nomeAluno;
  final double saldo;
  final List<int> versao;

  factory Conta.fromJson(Map<String, dynamic> json) => Conta(
        id: (json['id'] as num).toInt(),
        nomeAluno: json['nomeAluno'] as String,
        saldo: (json['saldo'] as num).toDouble(),
        versao: (json['versao'] as List).map((e) => (e as num).toInt()).toList(),
      );

  Map<String, dynamic> toJson() => {'id': id, 'nomeAluno': nomeAluno, 'saldo': saldo, 'versao': versao};

  Conta copyWith({double? saldo, List<int>? versao}) =>
      Conta(id: id, nomeAluno: nomeAluno, saldo: saldo ?? this.saldo, versao: versao ?? this.versao);
}

/// O que uma agencia diz sobre a lideranca (GET /bully/lider).
class AgenciaLideranca {
  const AgenciaLideranca({required this.idAgencia, required this.online, this.liderId});

  final int idAgencia;
  final bool online;
  final int? liderId;
}

class MovimentoExtrato {
  const MovimentoExtrato({required this.descricao, required this.valor, required this.horaParede});

  final String descricao;
  final double valor;
  final String horaParede;

  factory MovimentoExtrato.fromJson(Map<String, dynamic> json) => MovimentoExtrato(
        descricao: json['descricao'] as String,
        valor: (json['valor'] as num).toDouble(),
        horaParede: json['horaParede'] as String,
      );
}
