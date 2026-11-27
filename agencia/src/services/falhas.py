"""Injecao de falhas para os testes da Parte D: derruba o processo em um ponto
exato do protocolo, UMA unica vez (um arquivo marcador no volume impede que a
agencia caia de novo a cada reinicio do Docker, o que viraria um loop).

Uso: FALHA_2PC=participante-apos-votar. Para repetir o cenario, apague
DATA_DIR/falha-*.consumida.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config


def falhar(ponto: str) -> None:
    if os.environ.get("FALHA_2PC") != ponto:
        return
    id_agencia = os.environ.get("AGENCIA_ID", "0")
    marcador = Path(config.DATA_DIR) / f"falha-{id_agencia}-{ponto}.consumida"
    if marcador.exists():
        return
    marcador.write_text(datetime.now(timezone.utc).isoformat())
    print(f"[FALHA INJETADA] {ponto}: derrubando a agencia {id_agencia} agora", file=sys.stderr, flush=True)
    os._exit(1)  # _exit: derruba na hora, sem handlers nem flush, como uma queda de verdade
