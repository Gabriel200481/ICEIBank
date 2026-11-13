"""Extrato por conta (funcionalidade adicional do Sprint 3, secao 2.1).

Nao ha tabela de transacoes: a fonte de verdade das movimentacoes e o log de
eventos da agencia (.jsonl). O extrato e uma VISAO derivada desse log - o que
tambem prova que o log guarda informacao suficiente para reconstruir o
historico de uma conta.
"""

from typing import Any


def _movimento(evento: dict[str, Any], id_conta: int) -> dict[str, Any] | None:
    """Converte um evento em uma linha de extrato da conta, ou None se o
    evento nao afeta o saldo dessa conta."""
    tipo = evento["tipo"]
    d = evento["detalhes"]

    if tipo == "CRIAR_CONTA" and d.get("id") == id_conta:
        return {"descricao": "Abertura de conta", "valor": d["saldoInicial"]}
    if tipo == "DEPOSITO" and d.get("id") == id_conta:
        return {"descricao": "Deposito", "valor": d["valor"]}
    if tipo == "SAQUE" and d.get("id") == id_conta:
        return {"descricao": "Saque", "valor": -d["valor"]}
    if tipo == "TRANSFERENCIA_DEBITO" and d.get("idOrigem") == id_conta:
        return {"descricao": f"Transferencia enviada para a conta {d['idDestino']}", "valor": -d["valor"]}
    if tipo == "TRANSFERENCIA_CREDITO" and d.get("idDestino") == id_conta:
        return {"descricao": f"Transferencia recebida da conta {d['idOrigem']}", "valor": d["valor"]}
    if tipo == "TRANSFERENCIA_CREDITO_REMOTO" and d.get("idConta") == id_conta:
        return {"descricao": f"Transferencia recebida da agencia {d['origemAgencia']}", "valor": d["valor"]}
    if tipo == "SYNC_APLICADO" and d.get("idConta") == id_conta:
        sinal = 1 if d["tipo"] == "DEPOSITO" else -1
        rotulo = "Deposito" if d["tipo"] == "DEPOSITO" else "Saque"
        return {"descricao": f"{rotulo} (sincronizado do app)", "valor": sinal * d["valor"]}
    return None


def montar_extrato(eventos: list[dict[str, Any]], id_conta: int) -> list[dict[str, Any]]:
    extrato = []
    for evento in eventos:
        movimento = _movimento(evento, id_conta)
        if movimento is None:
            continue
        movimento["tipo"] = evento["tipo"]
        movimento["horaParede"] = evento["horaParede"]
        movimento["versao"] = evento["timestampVetorial"]
        extrato.append(movimento)
    return extrato
