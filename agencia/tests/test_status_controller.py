import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services import auth_service


@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=1)
    app.state.registro.caminho_arquivo = tmp_path / "eventos-teste.jsonl"
    cliente = TestClient(app)
    cliente.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    return cliente


def test_status_nao_exige_autenticacao(cliente):
    cliente.headers.pop("Authorization")
    resposta = cliente.get("/status")
    assert resposta.status_code == 200


def test_status_reporta_id_agencia_e_contador_zerado_sem_contas(cliente):
    resposta = cliente.get("/status")
    corpo = resposta.json()
    assert corpo["idAgencia"] == 1
    assert corpo["quantidadeContas"] == 0
    assert corpo["timestampLamportAtual"] == 0


def test_status_reflete_contas_criadas_e_relogio_atualizado(cliente):
    cliente.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})
    cliente.post("/contas", json={"id": 4, "nomeAluno": "Caio", "saldoInicial": 0})

    resposta = cliente.get("/status")
    corpo = resposta.json()
    assert corpo["quantidadeContas"] == 2
    assert corpo["timestampLamportAtual"] == 2
