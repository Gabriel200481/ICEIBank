from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.controllers import transferencias_controller
from src.services import auth_service


def _criar_cliente(tmp_path, id_agencia):
    app = criar_app(id_agencia=id_agencia)
    app.state.registro.caminho_arquivo = tmp_path / f"eventos-agencia-{id_agencia}.jsonl"
    cliente = TestClient(app)
    # rotas de contas/transferencias exigem JWT de usuario (Parte F);
    # creditar-remoto exige o service token, anexado a parte na chamada real.
    cliente.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    return app, cliente


@pytest.fixture
def cliente(tmp_path):
    _, cliente = _criar_cliente(tmp_path, id_agencia=0)
    return cliente


def test_transferencia_local_mesma_agencia(cliente):
    # conta 0 e conta 3 pertencem as duas a agencia 0 (0%3 == 3%3 == 0)
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente.post("/contas", json={"id": 3, "nomeAluno": "Bia", "saldoInicial": 10})

    resposta = cliente.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": 30})

    assert resposta.status_code == 200
    assert "mesma agencia" in resposta.json()["mensagem"]
    assert cliente.get("/contas/0").json()["saldo"] == 70
    assert cliente.get("/contas/3").json()["saldo"] == 40


def test_transferencia_conta_origem_nao_encontrada(cliente):
    resposta = cliente.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": 30})
    assert resposta.status_code == 404


def test_transferencia_saldo_insuficiente(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 10})
    cliente.post("/contas", json={"id": 3, "nomeAluno": "Bia", "saldoInicial": 0})
    resposta = cliente.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": 500})
    assert resposta.status_code == 400


def test_transferencia_entre_agencias_sucesso(tmp_path, monkeypatch):
    app_origem, cliente_origem = _criar_cliente(tmp_path, id_agencia=0)
    app_destino, cliente_destino = _criar_cliente(tmp_path, id_agencia=1)

    cliente_origem.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente_destino.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})

    def fake_post(url, json=None, headers=None, timeout=None):
        caminho = urlparse(url).path
        return cliente_destino.post(caminho, json=json, headers=headers)

    monkeypatch.setattr(transferencias_controller.httpx, "post", fake_post)

    resposta = cliente_origem.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 40})

    assert resposta.status_code == 200
    assert "entre agencias" in resposta.json()["mensagem"]
    assert cliente_origem.get("/contas/0").json()["saldo"] == 60
    assert cliente_destino.get("/contas/1").json()["saldo"] == 40

    # regra 3 de Lamport: quem recebe ajusta para max(local, recebido) + 1
    assert app_destino.state.relogio.contador > app_origem.state.relogio.contador - 1


def test_transferencia_entre_agencias_falha_agencia_fora_do_ar(tmp_path, monkeypatch):
    app_origem, cliente_origem = _criar_cliente(tmp_path, id_agencia=0)
    cliente_origem.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})

    def fake_post_falha(url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("Connection refused - agencia de destino fora do ar")

    monkeypatch.setattr(transferencias_controller.httpx, "post", fake_post_falha)

    resposta = cliente_origem.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 40})

    assert resposta.status_code == 502
    # LIMITACAO CONHECIDA: o debito ja aplicado NAO e revertido.
    assert cliente_origem.get("/contas/0").json()["saldo"] == 60

    linhas = app_origem.state.registro.caminho_arquivo.read_text(encoding="utf-8").strip().splitlines()
    tipos = [linha for linha in linhas if '"TRANSFERENCIA_FALHOU"' in linha]
    assert len(tipos) == 1


def test_creditar_remoto_usa_ao_receber_do_relogio_de_lamport(tmp_path):
    app_destino, cliente_destino = _criar_cliente(tmp_path, id_agencia=1)
    cliente_destino.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})

    app_destino.state.relogio.contador = 10  # agencia de destino "adiantada"

    resposta = cliente_destino.post(
        "/contas/1/creditar-remoto",
        json={"valor": 50, "timestampLamport": 3, "origemAgencia": 0},
        headers={"Authorization": f"Service {auth_service.SERVICE_TOKEN}"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["saldoAtual"] == 50
    # max(10, 3) + 1 = 11
    assert app_destino.state.relogio.contador == 11
