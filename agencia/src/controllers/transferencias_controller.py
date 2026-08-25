import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src import config

router = APIRouter()


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


class CreditoRemotoBody(BaseModel):
    valor: float
    timestampLamport: int
    origemAgencia: int


@router.post("/transferencias")
def transferir(body: TransferenciaBody, request: Request):
    estado = request.app.state

    conta_origem = estado.contas.get(body.idOrigem)
    if not conta_origem:
        raise HTTPException(status_code=404, detail="Conta de origem nao encontrada nesta agencia.")
    if conta_origem["saldo"] < body.valor:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    agencia_destino = config.agencia_responsavel(body.idDestino)

    # O debito e sempre local, pois esta agencia e a dona da conta de origem.
    ts_debito = estado.relogio.evento_local()
    conta_origem["saldo"] -= body.valor
    estado.registro.registrar(
        "TRANSFERENCIA_DEBITO",
        ts_debito,
        {"idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor},
    )

    if agencia_destino == estado.id_agencia:
        # Caso simples: mesma agencia, credita direto (nao precisa de
        # ao_enviar()/ao_receber() - nao ha mensagem cruzando processos).
        conta_destino = estado.contas.get(body.idDestino)
        if not conta_destino:
            conta_origem["saldo"] += body.valor
            raise HTTPException(status_code=404, detail="Conta de destino nao encontrada.")
        ts_credito = estado.relogio.evento_local()
        conta_destino["saldo"] += body.valor
        estado.registro.registrar(
            "TRANSFERENCIA_CREDITO",
            ts_credito,
            {"idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor},
        )
        return {"mensagem": "Transferencia concluida (mesma agencia)."}

    # Caso entre agencias: chama a agencia de destino diretamente via REST.
    ts_envio = estado.relogio.ao_enviar()
    url_destino = config.url_da_agencia(agencia_destino)

    try:
        resposta = httpx.post(
            f"{url_destino}/contas/{body.idDestino}/creditar-remoto",
            json={"valor": body.valor, "timestampLamport": ts_envio, "origemAgencia": estado.id_agencia},
            timeout=5.0,
        )
        resposta.raise_for_status()
        return {"mensagem": "Transferencia concluida (entre agencias)."}
    except httpx.HTTPError as erro:
        # LIMITACAO CONHECIDA: se esta chamada falhar, o debito ja aplicado
        # acima NAO e revertido - o dinheiro "desaparece" temporariamente.
        # Resolver isso de forma correta (atomicidade sob falha) e o assunto
        # do Sprint 4, com uma transacao distribuida de verdade (2PC/Saga).
        # Por enquanto, so registramos a inconsistencia no log.
        estado.registro.registrar(
            "TRANSFERENCIA_FALHOU",
            estado.relogio.evento_local(),
            {"idOrigem": body.idOrigem, "idDestino": body.idDestino, "valor": body.valor, "erro": str(erro)},
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao contatar agencia de destino. Debito ja aplicado - inconsistencia conhecida (ver Sprint 4).",
        )


@router.post("/contas/{id_conta}/creditar-remoto")
def creditar_remoto(id_conta: int, body: CreditoRemotoBody, request: Request):
    estado = request.app.state

    # Ao RECEBER uma mensagem de outra agencia, o relogio de Lamport e
    # atualizado com base no timestamp recebido - regra 3 do algoritmo.
    ts = estado.relogio.ao_receber(body.timestampLamport)

    conta = estado.contas.get(id_conta)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta nao encontrada nesta agencia.")

    conta["saldo"] += body.valor
    estado.registro.registrar(
        "TRANSFERENCIA_CREDITO_REMOTO",
        ts,
        {"idConta": id_conta, "valor": body.valor, "origemAgencia": body.origemAgencia},
    )
    return {"mensagem": "Credito remoto aplicado.", "saldoAtual": conta["saldo"]}
