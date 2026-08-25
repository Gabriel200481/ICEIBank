import json

from src.services.event_log import RegistroEventos


def test_registrar_grava_linha_jsonl_valida(tmp_path):
    registro = RegistroEventos("agencia-teste", pasta_dados=str(tmp_path))

    evento = registro.registrar("CRIAR_CONTA", 1, {"id": 0, "nomeAluno": "Ana"})

    assert evento["agencia"] == "agencia-teste"
    assert evento["tipo"] == "CRIAR_CONTA"
    assert evento["timestampLamport"] == 1
    assert "horaParede" in evento

    caminho = tmp_path / "eventos-agencia-teste.jsonl"
    assert caminho.exists()
    linhas = caminho.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1
    assert json.loads(linhas[0])["tipo"] == "CRIAR_CONTA"


def test_registrar_multiplos_eventos_faz_append(tmp_path):
    registro = RegistroEventos("agencia-teste", pasta_dados=str(tmp_path))
    registro.registrar("CRIAR_CONTA", 1, {"id": 0})
    registro.registrar("DEPOSITO", 2, {"id": 0, "valor": 50})

    caminho = tmp_path / "eventos-agencia-teste.jsonl"
    linhas = caminho.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2
    assert json.loads(linhas[1])["tipo"] == "DEPOSITO"
