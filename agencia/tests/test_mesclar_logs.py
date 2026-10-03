import json

from mesclar_logs import carregar_eventos, comparar_vetores, encontrar_pares_concorrentes


def _escrever_jsonl(caminho, eventos):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        for evento in eventos:
            arquivo.write(json.dumps(evento) + "\n")


def _evento(agencia, tipo, vetor, hora_parede):
    return {"agencia": agencia, "tipo": tipo, "timestampVetorial": vetor, "horaParede": hora_parede, "detalhes": {}}


def test_carrega_e_ordena_eventos_por_hora_de_parede(tmp_path):
    _escrever_jsonl(
        tmp_path / "eventos-agencia-0.jsonl",
        [_evento("agencia-0", "CRIAR_CONTA", [1, 0, 0], "2026-01-01T00:00:03Z")],
    )
    _escrever_jsonl(
        tmp_path / "eventos-agencia-1.jsonl",
        [_evento("agencia-1", "CRIAR_CONTA", [0, 1, 0], "2026-01-01T00:00:01Z")],
    )

    eventos = carregar_eventos(tmp_path)

    assert [e["agencia"] for e in eventos] == ["agencia-1", "agencia-0"]


def test_pasta_sem_eventos_retorna_lista_vazia(tmp_path):
    assert carregar_eventos(tmp_path) == []


def test_comparar_vetores_antes():
    assert comparar_vetores([3, 1, 0], [3, 2, 0]) == "ANTES"


def test_comparar_vetores_depois():
    assert comparar_vetores([3, 2, 0], [3, 1, 0]) == "DEPOIS"


def test_comparar_vetores_concorrentes():
    assert comparar_vetores([3, 1, 0], [1, 3, 0]) == "CONCORRENTES"


def test_comparar_vetores_iguais():
    assert comparar_vetores([2, 2, 0], [2, 2, 0]) == "IGUAIS"


def test_encontrar_pares_concorrentes_ignora_eventos_da_mesma_agencia(tmp_path):
    # mesma agencia, vetores que seriam "concorrentes" se fossem de agencias
    # diferentes - mas eventos de uma mesma agencia sao sempre sequenciais
    # (o relogio dela so anda pra frente), entao nao fazem sentido comparar.
    eventos = [
        _evento("agencia-0", "A", [3, 1, 0], "2026-01-01T00:00:01Z"),
        _evento("agencia-0", "B", [1, 3, 0], "2026-01-01T00:00:02Z"),
    ]
    assert encontrar_pares_concorrentes(eventos) == []


def test_encontrar_pares_concorrentes_detecta_concorrencia_real_entre_agencias(tmp_path):
    # Duas agencias criando contas de forma totalmente independente, sem
    # nenhuma mensagem entre elas - genuinamente concorrentes.
    eventos = [
        _evento("agencia-0", "CRIAR_CONTA", [1, 0, 0], "2026-01-01T00:00:01Z"),
        _evento("agencia-1", "CRIAR_CONTA", [0, 1, 0], "2026-01-01T00:00:01.5Z"),
    ]
    pares = encontrar_pares_concorrentes(eventos)
    assert len(pares) == 1
    assert {pares[0][0]["agencia"], pares[0][1]["agencia"]} == {"agencia-0", "agencia-1"}


def test_encontrar_pares_concorrentes_nao_inclui_par_causal_de_transferencia(tmp_path):
    # Debito na agencia 0 (vetor [2,0,0]) causa o credito na agencia 1
    # (vetor [2,1,0], que domina o do debito em toda posicao) - tem relacao
    # causal real, entao NAO deve aparecer como concorrente.
    eventos = [
        _evento("agencia-0", "TRANSFERENCIA_DEBITO", [2, 0, 0], "2026-01-01T00:00:01Z"),
        _evento("agencia-1", "TRANSFERENCIA_CREDITO_REMOTO", [2, 1, 0], "2026-01-01T00:00:02Z"),
    ]
    assert encontrar_pares_concorrentes(eventos) == []
