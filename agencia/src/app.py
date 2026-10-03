"""ICEIBank - servico de agencia.

Cada instancia deste app representa uma agencia. A identidade da agencia
(id_agencia) e definida pela variavel de ambiente AGENCIA_ID na subida do
processo, ou passada diretamente para criar_app() (usado nos testes, para
isolar o estado de cada instancia).
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import config
from src.controllers import auth_controller, contas_controller, status_controller, transferencias_controller
from src.services import mensageria
from src.services.event_log import RegistroEventos
from src.services.vector_clock import RelogioVetorial


def criar_app(id_agencia: int | None = None, iniciar_consumidor: bool = True) -> FastAPI:
    if id_agencia is None:
        id_agencia = int(os.environ.get("AGENCIA_ID", "0"))

    agencia_config = next((a for a in config.AGENCIAS if a["id"] == id_agencia), None)
    if agencia_config is None:
        raise RuntimeError(f"Agencia {id_agencia} nao configurada em config.py")

    app = FastAPI(title=f"ICEIBank - Agencia {id_agencia}")

    # CORS liberado (dev): o frontend estatico (servido em outra porta/origem)
    # precisa chamar a API diretamente do navegador. Aceitavel neste sprint
    # por nao haver cookies/sessao - so o JWT no header Authorization.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Estado em memoria da agencia - sem banco de dados neste sprint (Parte C).
    relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
    registro = RegistroEventos(f"agencia-{id_agencia}")
    contas: dict = {}

    app.state.id_agencia = id_agencia
    app.state.relogio = relogio
    app.state.registro = registro
    app.state.contas = contas

    app.include_router(auth_controller.router)
    app.include_router(contas_controller.router)
    app.include_router(transferencias_controller.router)
    app.include_router(status_controller.router)

    @app.get("/")
    def raiz():
        return {"servico": "ICEIBank - Agencia", "idAgencia": id_agencia, "status": "ok"}

    def _processar_credito_recebido(mensagem: dict) -> None:
        """Consumidor da fila da agencia (Sprint 2): aplica um credito
        publicado por outra agencia. Roda numa thread separada do servidor
        HTTP - ver src/services/mensageria.py.
        """
        id_conta = mensagem["idConta"]
        valor = mensagem["valor"]
        vetor_envio = mensagem["vetorEnvio"]
        origem_agencia = mensagem["origemAgencia"]

        # Ao RECEBER uma mensagem de outra agencia, o relogio vetorial e
        # atualizado com base no vetor recebido - regra 3 do algoritmo.
        vetor = relogio.ao_receber(vetor_envio)

        conta = contas.get(id_conta)
        if not conta:
            # Limitacao conhecida deste sprint (ver RESPOSTAS.md): as contas
            # vivem em memoria, sem persistencia. Se a agencia de destino
            # reiniciar antes de consumir a mensagem, a conta que deveria
            # receber o credito nao existe mais quando a mensagem chega.
            registro.registrar(
                "CREDITO_REMOTO_FALHOU",
                vetor,
                {"idConta": id_conta, "valor": valor, "origemAgencia": origem_agencia, "motivo": "conta nao encontrada"},
            )
            return

        conta["saldo"] += valor
        registro.registrar(
            "TRANSFERENCIA_CREDITO_REMOTO",
            vetor,
            {"idConta": id_conta, "valor": valor, "origemAgencia": origem_agencia},
        )

    # Exposto em app.state para ser testavel sem precisar de um broker real
    # (os testes chamam essa funcao diretamente, simulando a entrega).
    app.state.processar_credito_recebido = _processar_credito_recebido

    if iniciar_consumidor:
        mensageria.assinar(id_agencia, _processar_credito_recebido)

    return app


app = criar_app()
