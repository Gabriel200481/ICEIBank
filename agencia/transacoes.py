"""Mostra, para cada agencia, as transacoes 2PC que ela conhece e em que estado
estao (Sprint 4, Parte E): a ferramenta para ver o protocolo trabalhando
durante os testes de falha.

Uso (PowerShell, agencias em localhost, como no docker compose):

    $env:TOKEN_INTERNO = "troque-este-segredo"
    python transacoes.py
"""

import httpx

from src import config


def descrever(agencia: dict) -> list[str]:
    try:
        resp = httpx.get(
            f"{agencia['url']}/2pc/transacoes", headers={"x-token-interno": config.TOKEN_INTERNO}, timeout=2
        )
    except httpx.HTTPError:
        return ["  fora do ar"]
    if resp.status_code != 200:
        return [f"  resposta {resp.status_code} (token interno correto?)"]

    dados = resp.json()
    linhas = [f"  [coordenador] {c['txId'][:8]}  estado={c['estado']}  decisao={c['decisao']}" for c in dados["coordenacoes"]]
    for p in dados["participacoes"]:
        op = p["operacao"]
        linhas.append(
            f"  [participante] {p['txId'][:8]}  {op['tipo']} conta {op['idConta']} valor {op['valor']}  estado={p['estado']}"
        )
    return linhas or ["  (nenhuma transacao)"]


if __name__ == "__main__":
    for agencia in config.AGENCIAS:
        print(f"\n=== Agencia {agencia['id']} ({agencia['url']}) ===")
        print("\n".join(descrever(agencia)))
