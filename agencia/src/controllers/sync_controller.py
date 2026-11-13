"""Sincronizacao offline-first (Sprint 3, Parte E).

O app guarda operacoes feitas sem rede e as envia, uma a uma e em ordem,
quando reconecta. Cada operacao leva o `vetorBase`: a versao (vetor) da conta
que o cliente conhecia quando a criou. O servidor compara esse vetor com a
versao atual da conta (comparar_vetores, funcao pura):

- IGUAIS ou DEPOIS: o cliente viu tudo o que o servidor tem -> aplica (200)
- ANTES: o servidor ja evoluiu alem do que o cliente viu -> conflito (409)
- CONCORRENTES: cliente e servidor mudaram a conta sem se conhecer -> 409

Conflito nunca aplica a operacao: devolve o estado atual da conta para o app
mostrar ao usuario decidir. A operacao e idempotente por `idOperacao`.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src import config
from src.controllers.auth_controller import exigir_usuario_autenticado
from src.services.vector_clock import comparar_vetores

router = APIRouter(dependencies=[Depends(exigir_usuario_autenticado)])


class OperacaoSync(BaseModel):
    idOperacao: str = Field(min_length=1)
    tipo: Literal["DEPOSITO", "SAQUE"]
    idConta: int
    valor: float = Field(gt=0)
    vetorBase: list[int]


@router.post("/sincronizar")
def sincronizar(op: OperacaoSync, request: Request):
    estado = request.app.state

    if len(op.vetorBase) != config.NUMERO_AGENCIAS:
        raise HTTPException(status_code=400, detail=f"vetorBase deve ter {config.NUMERO_AGENCIAS} posicoes.")

    conta = estado.contas.get(op.idConta)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")

    # Idempotencia: reenviar a mesma operacao (ex.: a resposta se perdeu na
    # rede) nao aplica duas vezes.
    if op.idOperacao in estado.operacoes_aplicadas:
        return {"status": "JA_APLICADA", "idOperacao": op.idOperacao, "conta": conta}

    relacao = comparar_vetores(op.vetorBase, conta["versao"])
    # Receber a operacao do cliente e um evento de "recebimento": o relogio
    # incorpora o que o cliente sabia (regra 3 do relogio vetorial).
    ts = estado.relogio.ao_receber(op.vetorBase)

    if relacao in ("ANTES", "CONCORRENTES"):
        estado.registro.registrar(
            "SYNC_CONFLITO",
            ts,
            {
                "idOperacao": op.idOperacao,
                "idConta": op.idConta,
                "tipo": op.tipo,
                "valor": op.valor,
                "vetorBase": op.vetorBase,
                "versaoServidor": conta["versao"],
                "relacao": relacao,
            },
        )
        return JSONResponse(
            status_code=409,
            content={
                "status": "CONFLITO",
                "relacao": relacao,
                "idOperacao": op.idOperacao,
                "vetorBase": op.vetorBase,
                "versaoServidor": conta["versao"],
                "conta": conta,
            },
        )

    if op.tipo == "SAQUE" and conta["saldo"] < op.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    conta["saldo"] += op.valor if op.tipo == "DEPOSITO" else -op.valor
    conta["versao"] = ts
    estado.operacoes_aplicadas[op.idOperacao] = op.idConta
    estado.registro.registrar(
        "SYNC_APLICADO",
        ts,
        {"idOperacao": op.idOperacao, "idConta": op.idConta, "tipo": op.tipo, "valor": op.valor, "novoSaldo": conta["saldo"]},
    )
    return {"status": "APLICADA", "idOperacao": op.idOperacao, "conta": conta}
