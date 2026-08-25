import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services import auth_service


@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=0)
    # isola os logs de teste do diretorio real agencia/data
    app.state.registro.caminho_arquivo = tmp_path / "eventos-teste.jsonl"
    cliente = TestClient(app)
    # rotas de contas exigem JWT (Parte F) - anexa um token valido por padrao,
    # os testes especificos de autenticacao ficam em test_auth_controller.py
    cliente.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    return cliente


def test_criar_conta_na_agencia_correta(cliente):
    resposta = cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    assert resposta.status_code == 201
    assert resposta.json() == {"id": 0, "nomeAluno": "Ana", "saldo": 100}


def test_criar_conta_que_nao_pertence_a_agencia(cliente):
    # conta 1 pertence a agencia 1 (1 % 3), nao a agencia 0
    resposta = cliente.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})
    assert resposta.status_code == 400


def test_criar_conta_duplicada(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    resposta = cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    assert resposta.status_code == 409


def test_consultar_saldo_existente(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    resposta = cliente.get("/contas/0")
    assert resposta.status_code == 200
    assert resposta.json()["saldo"] == 100


def test_consultar_saldo_inexistente(cliente):
    resposta = cliente.get("/contas/0")
    assert resposta.status_code == 404


def test_depositar_aumenta_saldo(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    resposta = cliente.post("/contas/0/depositar", json={"valor": 25})
    assert resposta.status_code == 200
    assert resposta.json()["saldo"] == 125


def test_depositar_em_conta_inexistente(cliente):
    resposta = cliente.post("/contas/0/depositar", json={"valor": 25})
    assert resposta.status_code == 404


def test_sacar_com_saldo_suficiente(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    resposta = cliente.post("/contas/0/sacar", json={"valor": 40})
    assert resposta.status_code == 200
    assert resposta.json()["saldo"] == 60


def test_sacar_com_saldo_insuficiente(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    resposta = cliente.post("/contas/0/sacar", json={"valor": 500})
    assert resposta.status_code == 400


def test_sacar_de_conta_inexistente(cliente):
    resposta = cliente.post("/contas/0/sacar", json={"valor": 10})
    assert resposta.status_code == 404


def test_cada_operacao_e_carimbada_com_relogio_de_lamport(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})  # ts 1
    cliente.post("/contas/0/depositar", json={"valor": 25})  # ts 2
    cliente.post("/contas/0/sacar", json={"valor": 10})  # ts 3
    app = cliente.app
    assert app.state.relogio.contador == 3
