"""Transferencias via 2PC (Sprint 4).

Qualquer agencia recebe o pedido do cliente, mas quem COORDENA e sempre a lider
eleita pelo Bully. Se a agencia que recebeu nao e a lider, encaminha o pedido.

Respostas: 200 COMMIT; 422 ABORT (com os motivos); 503 sem lider ou lider
inacessivel (nada foi aplicado, ou o 2PC resolve sozinho na recuperacao).
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import config
from src.controllers.auth_controller import exigir_usuario_autenticado
from src.middlewares.autenticacao_interna import autenticacao_interna

router = APIRouter()

TIMEOUT_ENCAMINHAR = 15.0


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


def _resposta(resumo: dict) -> JSONResponse:
    # "mensagem" (200) e "detail" (erro) mantem o contrato que o frontend e o app ja leem.
    if resumo["resultado"] == "COMMIT":
        return JSONResponse(status_code=200, content={**resumo, "mensagem": "Transferencia concluida (2PC: COMMIT)."})
    detalhe = "Transferencia abortada: " + "; ".join(m for m in resumo["motivos"] if m)
    return JSONResponse(status_code=422, content={**resumo, "detail": detalhe})


@router.post("/transferencias", dependencies=[Depends(exigir_usuario_autenticado)])
def transferir(body: TransferenciaBody, request: Request):
    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero.")
    if body.idOrigem == body.idDestino:
        raise HTTPException(status_code=400, detail="Origem e destino devem ser diferentes.")

    estado = request.app.state
    lider = estado.bully.lider_atual
    if lider is None:
        raise HTTPException(status_code=503, detail="Sem lider eleito no momento. Tente novamente.")

    try:
        if lider == estado.id_agencia:
            return _resposta(estado.coordenador.coordenar(body.idOrigem, body.idDestino, body.valor))
        status, corpo = estado.coordenador.cliente.encaminhar(
            config.url_da_agencia(lider) + "/2pc/coordenar", body.model_dump(), TIMEOUT_ENCAMINHAR
        )
        return JSONResponse(status_code=status, content=corpo)
    except (httpx.HTTPError, ValueError, ConnectionError):
        raise HTTPException(status_code=503, detail="Coordenador indisponivel. O resultado sera resolvido sozinho: confira os saldos antes de tentar de novo.",
        )


@router.post("/2pc/coordenar", dependencies=[Depends(autenticacao_interna)])
def coordenar_a_requisicao(body: TransferenciaBody, request: Request):
    """Rota interna: outra agencia pede para esta lider coordenar."""
    estado = request.app.state
    if estado.bully.lider_atual != estado.id_agencia:
        raise HTTPException(status_code=409, detail="Esta agencia nao e a lider.")
    return _resposta(estado.coordenador.coordenar(body.idOrigem, body.idDestino, body.valor))
