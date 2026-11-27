"""Rotas internas do 2PC (chamadas apenas por outras agencias, com x-token-interno)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.middlewares.autenticacao_interna import autenticacao_interna

router = APIRouter(prefix="/2pc", dependencies=[Depends(autenticacao_interna)])


class Operacao(BaseModel):
    tipo: str
    idConta: int
    valor: float


class PrepararBody(BaseModel):
    txId: str
    operacao: Operacao
    coordenador: int
    vetorEnvio: list[int] | None = None


class DecidirBody(BaseModel):
    txId: str
    decisao: str
    vetorEnvio: list[int] | None = None


@router.post("/preparar")
def preparar(body: PrepararBody, request: Request):
    return request.app.state.participante.preparar(
        body.txId, body.operacao.model_dump(), body.coordenador, body.vetorEnvio
    )


@router.post("/decidir")
def decidir(body: DecidirBody, request: Request):
    resposta = request.app.state.participante.decidir(body.txId, body.decisao, body.vetorEnvio)
    return JSONResponse(status_code=409 if "erro" in resposta else 200, content=resposta)


@router.get("/status/{tx_id}")
def status(tx_id: str, request: Request):
    return request.app.state.coordenador.status_de(tx_id)


@router.get("/transacoes")
def transacoes(request: Request):
    estado = request.app.state
    with estado.estado.lock:
        return {
            "coordenacoes": list(estado.estado.coordenacoes.values()),
            "participacoes": list(estado.estado.participacoes.values()),
            "vetor": estado.relogio.vetor,
        }
