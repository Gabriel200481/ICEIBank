import 'models.dart';

enum EstadoOperacao {
  /// Aguardando envio ao servidor.
  pendente,

  /// O servidor recusou por conflito de versao (HTTP 409): precisa de decisao do usuario.
  conflito,

  /// O servidor recusou por regra de negocio (ex.: saldo insuficiente).
  rejeitada,
}

class OperacaoPendente {
  const OperacaoPendente({
    required this.idOperacao,
    required this.tipo,
    required this.idConta,
    required this.valor,
    required this.vetorBase,
    required this.criadaEm,
    this.estado = EstadoOperacao.pendente,
    this.mensagem,
    this.contaServidor,
  });

  final String idOperacao;

  /// 'DEPOSITO' ou 'SAQUE' (as unicas operacoes aceitas por POST /sincronizar).
  final String tipo;
  final int idConta;
  final double valor;

  /// Versao da conta que o app conhecia quando criou a operacao.
  final List<int> vetorBase;
  final DateTime criadaEm;
  final EstadoOperacao estado;
  final String? mensagem;

  /// Estado da conta no servidor no momento do conflito (para o usuario decidir).
  final Conta? contaServidor;

  double get efeitoNoSaldo => tipo == 'DEPOSITO' ? valor : -valor;

  OperacaoPendente copyWith({
    EstadoOperacao? estado,
    String? mensagem,
    Conta? contaServidor,
    List<int>? vetorBase,
  }) =>
      OperacaoPendente(
        idOperacao: idOperacao,
        tipo: tipo,
        idConta: idConta,
        valor: valor,
        vetorBase: vetorBase ?? this.vetorBase,
        criadaEm: criadaEm,
        estado: estado ?? this.estado,
        mensagem: mensagem ?? this.mensagem,
        contaServidor: contaServidor ?? this.contaServidor,
      );

  Map<String, dynamic> toJson() => {
        'idOperacao': idOperacao,
        'tipo': tipo,
        'idConta': idConta,
        'valor': valor,
        'vetorBase': vetorBase,
        'criadaEm': criadaEm.toIso8601String(),
        'estado': estado.name,
        'mensagem': mensagem,
        'contaServidor': contaServidor?.toJson(),
      };

  factory OperacaoPendente.fromJson(Map<String, dynamic> json) => OperacaoPendente(
        idOperacao: json['idOperacao'] as String,
        tipo: json['tipo'] as String,
        idConta: (json['idConta'] as num).toInt(),
        valor: (json['valor'] as num).toDouble(),
        vetorBase: (json['vetorBase'] as List).map((e) => (e as num).toInt()).toList(),
        criadaEm: DateTime.parse(json['criadaEm'] as String),
        estado: EstadoOperacao.values.byName(json['estado'] as String),
        mensagem: json['mensagem'] as String?,
        contaServidor: json['contaServidor'] == null ? null : Conta.fromJson(json['contaServidor'] as Map<String, dynamic>),
      );
}
