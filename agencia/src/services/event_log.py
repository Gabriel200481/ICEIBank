"""Registro de eventos de uma agencia em um arquivo .jsonl (append-only).

Cada linha e um evento JSON com o timestamp logico (Lamport) e o timestamp
de parede (relogio fisico da maquina, so para comparacao - nao usado em
nenhuma decisao do sistema).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RegistroEventos:
    def __init__(self, nome_agencia: str, pasta_dados: str | None = None) -> None:
        self.nome_agencia = nome_agencia
        base = Path(pasta_dados) if pasta_dados else Path(__file__).resolve().parent.parent.parent / "data"
        base.mkdir(parents=True, exist_ok=True)
        self.caminho_arquivo = base / f"eventos-{nome_agencia}.jsonl"

    def registrar(self, tipo: str, timestamp_lamport: int, detalhes: dict[str, Any]) -> dict[str, Any]:
        evento = {
            "agencia": self.nome_agencia,
            "tipo": tipo,
            "timestampLamport": timestamp_lamport,
            "horaParede": datetime.now(timezone.utc).isoformat(),
            "detalhes": detalhes,
        }
        # newline="" evita que o Python traduza "\n" para o separador do SO
        # (no Windows isso geraria "\r\r\n" e linhas em branco no .jsonl).
        with open(self.caminho_arquivo, "a", encoding="utf-8", newline="") as arquivo:
            arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
        print(f"[Lamport {timestamp_lamport}] {tipo} {detalhes}")
        return evento
