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
from src.services.event_log import RegistroEventos
from src.services.lamport_clock import RelogioLamport


def criar_app(id_agencia: int | None = None) -> FastAPI:
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
    app.state.id_agencia = id_agencia
    app.state.relogio = RelogioLamport()
    app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
    app.state.contas = {}

    app.include_router(auth_controller.router)
    app.include_router(contas_controller.router)
    app.include_router(transferencias_controller.router)
    app.include_router(status_controller.router)

    @app.get("/")
    def raiz():
        return {"servico": "ICEIBank - Agencia", "idAgencia": id_agencia, "status": "ok"}

    return app


app = criar_app()
