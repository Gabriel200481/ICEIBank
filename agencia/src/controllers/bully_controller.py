"""Rotas do algoritmo de Bully (Sprint 3).

Sem JWT de proposito: sao chamadas entre agencias (maquina a maquina), nao de
um usuario. No Sprint 4 /eleicao e /coordenador passaram a exigir o token
interno compartilhado (x-token-interno); GET /lider continua publico porque o
app Flutter e o heartbeat dependem dele.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.middlewares.autenticacao_interna import autenticacao_interna

router = APIRouter(prefix="/bully")


class EleicaoBody(BaseModel):
    origemId: int
    vetor: list[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetor: list[int]


@router.post("/eleicao", dependencies=[Depends(autenticacao_interna)])
def eleicao(body: EleicaoBody, request: Request):
    return request.app.state.bully.receber_eleicao(body.origemId, body.vetor)


@router.post("/coordenador", dependencies=[Depends(autenticacao_interna)])
def coordenador(body: CoordenadorBody, request: Request):
    request.app.state.bully.receber_coordenador(body.liderId, body.vetor)
    return {"mensagem": "Coordenador registrado."}


@router.get("/lider")
def lider(request: Request):
    estado = request.app.state
    return {"liderId": estado.bully.lider_atual, "idAgencia": estado.id_agencia}
