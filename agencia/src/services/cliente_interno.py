"""Cliente HTTP para falar com as OUTRAS agencias nas rotas internas (2PC).

Anexa o token compartilhado. Qualquer falha (rede, timeout, status != 2xx)
levanta excecao: quem chama decide o que significa (no voto, vira NAO).
"""

import httpx

from src import config


def _cabecalhos() -> dict:
    return {"x-token-interno": config.TOKEN_INTERNO}


def post(url: str, corpo: dict, timeout: float) -> dict:
    resposta = httpx.post(url, json=corpo, headers=_cabecalhos(), timeout=timeout)
    resposta.raise_for_status()
    return resposta.json()


def get(url: str, timeout: float) -> dict:
    resposta = httpx.get(url, headers=_cabecalhos(), timeout=timeout)
    resposta.raise_for_status()
    return resposta.json()


def encaminhar(url: str, corpo: dict, timeout: float) -> tuple[int, dict]:
    """POST que devolve (status, corpo) mesmo em erro: usado para repassar a
    resposta da lider (200 COMMIT, 422 ABORT...) ao cliente."""
    resposta = httpx.post(url, json=corpo, headers=_cabecalhos(), timeout=timeout)
    return resposta.status_code, resposta.json()
