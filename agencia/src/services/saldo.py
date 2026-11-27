def saldo_disponivel(conta: dict) -> float:
    """Saldo que pode ser gasto agora: o saldo menos o que esta reservado por
    transacoes distribuidas ainda nao concluidas."""
    return conta["saldo"] - conta.get("reservado", 0)
