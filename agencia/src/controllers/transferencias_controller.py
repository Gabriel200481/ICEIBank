from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src import config
from src.controllers.auth_controller import exigir_usuario_autenticado
from src.services import mensageria

router = APIRouter()


class TransferenciaBody(BaseModel):
    idOrigem: int
    idDestino: int
    valor: float


@router.post("/transferencias", dependencies=[Depends(exigir_usuario_autenticado)])
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

    # Caso entre agencias (Sprint 2): em vez de chamar a outra agencia
    # diretamente via REST (Sprint 1), publica um evento na exchange do
    # RabbitMQ. A agencia de destino consome quando estiver disponivel -
    # mesmo que esteja fora do ar agora, a mensagem fica retida na fila
    # (durable) e e entregue quando ela voltar.
    ts_envio = estado.relogio.ao_enviar()
    mensageria.publicar(
        f"agencia.{agencia_destino}.creditar",
        {
            "idConta": body.idDestino,
            "valor": body.valor,
            "vetorEnvio": ts_envio,
            "origemAgencia": estado.id_agencia,
        },
    )

    # Repare a mudanca de sentido em relacao ao Sprint 1: 200 aqui significa
    # apenas "a mensagem foi publicada", nao "o credito ja foi aplicado na
    # outra agencia" - a aplicacao efetiva acontece de forma assincrona, em
    # um momento que quem chamou nao controla nem confirma na hora.
    return {"mensagem": "Transferencia publicada para a agencia de destino (entrega assincrona)."}
