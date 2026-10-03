"""Le os .jsonl de todas as agencias e monta uma linha do tempo unica
(ordenada por hora de parede, so para leitura humana - vetores nao tem uma
ordem total, entao nao faz sentido "ordenar" por eles), e identifica pares
de eventos comprovadamente concorrentes comparando os vetores de relogio -
algo que o relogio de Lamport (Sprint 1), sozinho, nunca garantiria.
"""

import json
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent / "data"


def carregar_eventos(pasta_dados: Path = PASTA_DADOS) -> list[dict]:
    eventos = []
    for arquivo in sorted(pasta_dados.glob("*.jsonl")):
        linhas = arquivo.read_text(encoding="utf-8").strip().splitlines()
        eventos.extend(json.loads(linha) for linha in linhas if linha)
    eventos.sort(key=lambda evento: evento["horaParede"])
    return eventos


def imprimir_linha_do_tempo(eventos: list[dict]) -> None:
    print("=== Linha do tempo (ordenada por hora de parede) ===")
    for evento in eventos:
        detalhes = json.dumps(evento["detalhes"], ensure_ascii=False)
        print(f"[{evento['agencia']}] vetor={evento['timestampVetorial']} {evento['tipo']} {detalhes}")


def comparar_vetores(v1: list[int], v2: list[int]) -> str:
    """ANTES: v1 aconteceu antes de v2 (v1 <= v2 em toda posicao).
    DEPOIS: v2 aconteceu antes de v1. CONCORRENTES: nenhum domina o outro.
    """
    v1_menor_ou_igual = all(v1[i] <= v2[i] for i in range(len(v1)))
    v2_menor_ou_igual = all(v2[i] <= v1[i] for i in range(len(v1)))
    if v1_menor_ou_igual and v2_menor_ou_igual:
        return "IGUAIS"
    if v1_menor_ou_igual:
        return "ANTES"
    if v2_menor_ou_igual:
        return "DEPOIS"
    return "CONCORRENTES"


def encontrar_pares_concorrentes(eventos: list[dict]) -> list[tuple[dict, dict]]:
    pares = []
    for i in range(len(eventos)):
        for j in range(i + 1, len(eventos)):
            e1, e2 = eventos[i], eventos[j]
            if e1["agencia"] == e2["agencia"]:
                continue
            if comparar_vetores(e1["timestampVetorial"], e2["timestampVetorial"]) == "CONCORRENTES":
                pares.append((e1, e2))
    return pares


def imprimir_pares_concorrentes(pares: list[tuple[dict, dict]]) -> None:
    print("\n=== Pares de eventos CONCORRENTES entre agencias diferentes ===")
    if not pares:
        print("(nenhum par concorrente encontrado nesta execucao - gere mais eventos em paralelo e rode de novo)")
        return
    for e1, e2 in pares:
        print(
            f"[{e1['agencia']}] {e1['tipo']} ({e1['timestampVetorial']})  x  "
            f"[{e2['agencia']}] {e2['tipo']} ({e2['timestampVetorial']})"
        )


def main() -> None:
    eventos = carregar_eventos()
    imprimir_linha_do_tempo(eventos)
    imprimir_pares_concorrentes(encontrar_pares_concorrentes(eventos))


if __name__ == "__main__":
    main()
