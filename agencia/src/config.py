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


# Segundos de espera antes da eleicao inicial (o servidor HTTP precisa estar
# no ar para as outras agencias conseguirem responder).
BULLY_ATRASO_INICIAL = float(os.environ.get("BULLY_ATRASO_INICIAL", "1.5"))

# Permite desligar a eleicao automatica (usado na suite de testes, para nao
# disparar threads de rede nem escrever nos logs reais ao importar o app).
BULLY_DESLIGADO = os.environ.get("BULLY_DESLIGADO", "") == "1"

# Heartbeat da lider (Sprint 3, Parte B): intervalo entre verificacoes e
# quantas falhas seguidas contam como "lider caiu".
HEARTBEAT_INTERVALO = float(os.environ.get("HEARTBEAT_INTERVALO", "2"))
HEARTBEAT_FALHAS = int(os.environ.get("HEARTBEAT_FALHAS", "2"))
