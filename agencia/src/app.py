"""ICEIBank - servico de agencia.

Cada instancia deste app representa uma agencia. A identidade da agencia
(idAgencia) e definida pela variavel de ambiente AGENCIA_ID na subida do
processo (ver Parte C - api-rest-mvc).
"""

from fastapi import FastAPI

app = FastAPI(title="ICEIBank - Agencia")


@app.get("/")
def raiz():
    return {"servico": "ICEIBank - Agencia", "status": "ok"}
