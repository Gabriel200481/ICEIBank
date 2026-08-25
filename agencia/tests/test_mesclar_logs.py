import json

from mesclar_logs import carregar_eventos


def _escrever_jsonl(caminho, eventos):
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        for evento in eventos:
            arquivo.write(json.dumps(evento) + "\n")


def _evento(agencia, tipo, ts):
    return {"agencia": agencia, "tipo": tipo, "timestampLamport": ts, "horaParede": "2026-01-01T00:00:00Z", "detalhes": {}}


def test_carrega_e_ordena_eventos_de_varias_agencias_por_lamport(tmp_path):
    _escrever_jsonl(tmp_path / "eventos-agencia-0.jsonl", [_evento("agencia-0", "CRIAR_CONTA", 3), _evento("agencia-0", "DEPOSITO", 5)])
    _escrever_jsonl(tmp_path / "eventos-agencia-1.jsonl", [_evento("agencia-1", "CRIAR_CONTA", 1), _evento("agencia-1", "SAQUE", 4)])

    eventos = carregar_eventos(tmp_path)

    timestamps = [e["timestampLamport"] for e in eventos]
    assert timestamps == [1, 3, 4, 5]


def test_preserva_eventos_com_timestamp_empatado_de_agencias_diferentes(tmp_path):
    _escrever_jsonl(tmp_path / "eventos-agencia-0.jsonl", [_evento("agencia-0", "CRIAR_CONTA", 2)])
    _escrever_jsonl(tmp_path / "eventos-agencia-1.jsonl", [_evento("agencia-1", "CRIAR_CONTA", 2)])

    eventos = carregar_eventos(tmp_path)

    assert len(eventos) == 2
    assert {e["agencia"] for e in eventos} == {"agencia-0", "agencia-1"}


def test_pasta_sem_eventos_retorna_lista_vazia(tmp_path):
    assert carregar_eventos(tmp_path) == []
