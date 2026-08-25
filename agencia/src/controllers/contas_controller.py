from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import config

router = APIRouter()


class CriarContaBody(BaseModel):
    id: int
    nomeAluno: str
    saldoInicial: float = 0


class ValorBody(BaseModel):
    valor: float


@router.post("/contas", status_code=201)
def criar_conta(body: CriarContaBody, request: Request):
    estado = request.app.state

    if config.agencia_responsavel(body.id) != estado.id_agencia:
        raise HTTPException(status_code=400, detail=f"Conta {body.id} nao pertence a esta agencia.")
    if body.id in estado.contas:
        raise HTTPException(status_code=409, detail="Conta ja existe.")

    ts = estado.relogio.evento_local()
    estado.contas[body.id] = {"id": body.id, "nomeAluno": body.nomeAluno, "saldo": body.saldoInicial}
    estado.registro.registrar(
        "CRIAR_CONTA", ts, {"id": body.id, "nomeAluno": body.nomeAluno, "saldoInicial": body.saldoInicial}
    )
    return estado.contas[body.id]


@router.get("/contas/{id_conta}")
def consultar_saldo(id_conta: int, request: Request):
    conta = request.app.state.contas.get(id_conta)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")
    return conta


@router.post("/contas/{id_conta}/depositar")
def depositar(id_conta: int, body: ValorBody, request: Request):
    estado = request.app.state
    conta = estado.contas.get(id_conta)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")

    ts = estado.relogio.evento_local()
    conta["saldo"] += body.valor
    estado.registro.registrar("DEPOSITO", ts, {"id": id_conta, "valor": body.valor, "novoSaldo": conta["saldo"]})
    return conta


@router.post("/contas/{id_conta}/sacar")
def sacar(id_conta: int, body: ValorBody, request: Request):
    estado = request.app.state
    conta = estado.contas.get(id_conta)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")
    if conta["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    ts = estado.relogio.evento_local()
    conta["saldo"] -= body.valor
    estado.registro.registrar("SAQUE", ts, {"id": id_conta, "valor": body.valor, "novoSaldo": conta["saldo"]})
    return conta
