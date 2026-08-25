"""Configuracao e particionamento de contas entre as agencias do ICEIBank.

Cada conta pertence a exatamente uma agencia (particao, nao replicacao):
dado o numero da conta, a agencia responsavel e id_conta % NUMERO_AGENCIAS.
"""

import os

# Dois ultimos digitos da matricula/RA - so importa em maquina compartilhada
# de laboratorio, para nao colidir de porta com outro aluno.
OFFSET = int(os.environ.get("OFFSET", "0"))

NUMERO_AGENCIAS = 3
PORTA_BASE = 4000 + OFFSET

AGENCIAS = [
    {"id": 0, "url": f"http://localhost:{PORTA_BASE}"},
    {"id": 1, "url": f"http://localhost:{PORTA_BASE + 1}"},
    {"id": 2, "url": f"http://localhost:{PORTA_BASE + 2}"},
]


def agencia_responsavel(id_conta: int) -> int:
    return id_conta % NUMERO_AGENCIAS


def url_da_agencia(id_agencia: int) -> str:
    return next(a["url"] for a in AGENCIAS if a["id"] == id_agencia)
