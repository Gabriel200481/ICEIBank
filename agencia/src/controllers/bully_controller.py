"""Rotas do algoritmo de Bully (Sprint 3).

Sem JWT de proposito: sao chamadas entre agencias (maquina a maquina), nao de
um usuario - o mesmo raciocinio do consumidor de mensagens do Sprint 2. Em
producao isso exigiria autenticacao entre servicos (mTLS ou token de servico);
ver RESPOSTAS.md.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/bully")


class EleicaoBody(BaseModel):
    origemId: int
    vetor: list[int]


class CoordenadorBody(BaseModel):
    liderId: int
    vetor: list[int]


@router.post("/eleicao")
def eleicao(body: EleicaoBody, request: Request):
    return request.app.state.bully.receber_eleicao(body.origemId, body.vetor)


@router.post("/coordenador")
def coordenador(body: CoordenadorBody, request: Request):
    request.app.state.bully.receber_coordenador(body.liderId, body.vetor)
    return {"mensagem": "Coordenador registrado."}


@router.get("/lider")
def lider(request: Request):
    estado = request.app.state
    return {"liderId": estado.bully.lider_atual, "idAgencia": estado.id_agencia}
