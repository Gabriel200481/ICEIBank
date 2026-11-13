"""Reconstroi a linha do tempo de liderancas a partir dos .jsonl das agencias
(Sprint 3, Parte C) - mesma ideia do mesclar_logs.py, mas olhando so os
eventos de eleicao: ELEICAO_INICIADA, NOVO_LIDER e LIDER_CAIU.

Cada agencia registra o proprio NOVO_LIDER, entao a mesma troca aparece ate
3 vezes (uma por agencia). O script agrupa essas linhas em UM mandato e
guarda quais agencias o reconheceram.

Observacao: a ordem e dada pela hora de parede (so para leitura humana).
Os vetores nao tem ordem total - ver mesclar_logs.py.
"""

import sys
from datetime import datetime
from pathlib import Path

from mesclar_logs import PASTA_DADOS, carregar_eventos

TIPOS = {"ELEICAO_INICIADA", "NOVO_LIDER", "LIDER_CAIU"}


def construir_mandatos(eventos: list[dict]) -> list[dict]:
    """Retorna uma lista de mandatos: {lider, inicio, fim, motivoFim,
    reconhecidoPor, eleicoesAntes}. `fim` e None no mandato em curso."""
    mandatos: list[dict] = []
    atual: dict | None = None
    eleicoes_pendentes = 0

    for evento in sorted((e for e in eventos if e["tipo"] in TIPOS), key=lambda e: e["horaParede"]):
        tipo = evento["tipo"]
        hora = evento["horaParede"]

        if tipo == "ELEICAO_INICIADA":
            eleicoes_pendentes += 1
        elif tipo == "NOVO_LIDER":
            lider = evento["detalhes"]["liderId"]
            if atual and atual["fim"] is None:
                if atual["lider"] == lider:
                    atual["reconhecidoPor"].add(evento["agencia"])
                    continue
                atual["fim"] = hora
                atual["motivoFim"] = "SUBSTITUIDA"
            atual = {
                "lider": lider,
                "inicio": hora,
                "fim": None,
                "motivoFim": None,
                "reconhecidoPor": {evento["agencia"]},
                "eleicoesAntes": eleicoes_pendentes,
            }
            eleicoes_pendentes = 0
            mandatos.append(atual)
        elif tipo == "LIDER_CAIU":
            if atual and atual["fim"] is None and atual["lider"] == evento["detalhes"]["liderId"]:
                atual["fim"] = hora
                atual["motivoFim"] = "QUEDA_DETECTADA"
    return mandatos


def _duracao(inicio: str, fim: str | None) -> str:
    if fim is None:
        return "em curso"
    segundos = (datetime.fromisoformat(fim) - datetime.fromisoformat(inicio)).total_seconds()
    return f"{segundos:.1f}s"


def imprimir_historico(mandatos: list[dict]) -> None:
    print("=== Historico de liderancas ===")
    if not mandatos:
        print("(nenhuma lideranca registrada - suba as agencias e rode de novo)")
        return
    print(f"{'#':<3}{'LIDER':<7}{'INICIO (UTC)':<15}{'FIM (UTC)':<15}{'DURACAO':<10}{'MOTIVO DO FIM':<17}RECONHECIDA POR")
    for numero, m in enumerate(mandatos, start=1):
        inicio = m["inicio"][11:23]
        fim = m["fim"][11:23] if m["fim"] else "-"
        reconhecida = ", ".join(sorted(m["reconhecidoPor"]))
        print(
            f"{numero:<3}{m['lider']:<7}{inicio:<15}{fim:<15}{_duracao(m['inicio'], m['fim']):<10}"
            f"{(m['motivoFim'] or '-'):<17}{reconhecida}"
        )


def main(argv: list[str]) -> None:
    pasta = Path(argv[1]) if len(argv) > 1 else PASTA_DADOS
    imprimir_historico(construir_mandatos(carregar_eventos(pasta)))


if __name__ == "__main__":
    main(sys.argv)
