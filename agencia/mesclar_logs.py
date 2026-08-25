"""Le os .jsonl de todas as agencias e monta uma linha do tempo unica,
ordenada por relogio de Lamport - para observar o algoritmo funcionando de
verdade sobre operacoes concorrentes das 3 agencias.
"""

import json
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent / "data"


def carregar_eventos(pasta_dados: Path = PASTA_DADOS) -> list[dict]:
    eventos = []
    for arquivo in sorted(pasta_dados.glob("*.jsonl")):
        linhas = arquivo.read_text(encoding="utf-8").strip().splitlines()
        eventos.extend(json.loads(linha) for linha in linhas if linha)
    eventos.sort(key=lambda evento: evento["timestampLamport"])
    return eventos


def imprimir_linha_do_tempo(eventos: list[dict]) -> None:
    print("=== Linha do tempo unificada (ordenada por relogio de Lamport) ===")
    for evento in eventos:
        detalhes = json.dumps(evento["detalhes"], ensure_ascii=False)
        print(
            f"[Lamport {evento['timestampLamport']}] ({evento['horaParede']}) "
            f"{evento['agencia']} - {evento['tipo']} {detalhes}"
        )


def main() -> None:
    imprimir_linha_do_tempo(carregar_eventos())


if __name__ == "__main__":
    main()
