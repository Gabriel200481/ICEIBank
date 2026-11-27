"""Configuracao e particionamento de contas entre as agencias do ICEIBank.

Cada conta pertence a exatamente uma agencia (particao, nao replicacao):
dado o numero da conta, a agencia responsavel e id_conta % NUMERO_AGENCIAS.
"""

import os
from pathlib import Path

# Dois ultimos digitos da matricula/RA - so importa em maquina compartilhada
# de laboratorio, para nao colidir de porta com outro aluno.
OFFSET = int(os.environ.get("OFFSET", "0"))

NUMERO_AGENCIAS = 3
PORTA_BASE = int(os.environ.get("PORTA_BASE", 4000 + OFFSET))

# Em containers as agencias se enxergam pelo nome do servico (agencia-0, ...);
# fora deles, tudo e localhost. AGENCIA_URL_<id> sobrescreve a URL inteira.
HOSTS = os.environ.get("AGENCIAS_HOSTS", "localhost,localhost,localhost").split(",")

AGENCIAS = [
    {"id": i, "url": os.environ.get(f"AGENCIA_URL_{i}") or f"http://{HOSTS[i]}:{PORTA_BASE + i}"}
    for i in range(NUMERO_AGENCIAS)
]

# Onde ficam os arquivos que precisam sobreviver a um reinicio (estado e logs).
# Em containers, aponta para um volume (/dados).
DATA_DIR = os.environ.get("DATA_DIR") or str(Path(__file__).resolve().parent.parent / "data")

# Segredo compartilhado entre as agencias para as rotas internas (Bully e 2PC).
# Vazio = rotas internas recusam tudo (falha fechada).
TOKEN_INTERNO = os.environ.get("TOKEN_INTERNO", "")

# Tempos do 2PC (segundos), configuraveis por ambiente (funcionalidade adicional).
TIMEOUT_2PC = float(os.environ.get("TIMEOUT_2PC", "2"))
INTERVALO_REENTREGA = float(os.environ.get("INTERVALO_REENTREGA", "3"))
INTERVALO_RESOLUCAO = float(os.environ.get("INTERVALO_RESOLUCAO", "3"))

# Topico SNS da nuvem local (Parte F). Vazio = a agencia nao publica eventos.
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")


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
