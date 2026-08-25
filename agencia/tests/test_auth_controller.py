from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services import auth_service


@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=0)
    app.state.registro.caminho_arquivo = tmp_path / "eventos-teste.jsonl"
    return TestClient(app)


def _token_expirado() -> str:
    agora = datetime.now(timezone.utc)
    payload = {"sub": "aluno", "iat": agora - timedelta(minutes=20), "exp": agora - timedelta(minutes=1)}
    return jwt.encode(payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)


def test_login_com_credenciais_corretas_retorna_token(cliente):
    resposta = cliente.post("/auth/login", json={"usuario": "aluno", "senha": "senha123"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert len(corpo["access_token"]) > 0


def test_login_com_credenciais_erradas_retorna_401(cliente):
    resposta = cliente.post("/auth/login", json={"usuario": "aluno", "senha": "errada"})
    assert resposta.status_code == 401


# --- Cenario 1: sem token -----------------------------------------------


def test_rota_protegida_sem_token_retorna_401(cliente):
    resposta = cliente.get("/contas/0")
    assert resposta.status_code == 401


# --- Cenario 2: com token valido ------------------------------------------


def test_rota_protegida_com_token_valido_funciona(cliente):
    login = cliente.post("/auth/login", json={"usuario": "aluno", "senha": "senha123"})
    token = login.json()["access_token"]

    resposta = cliente.post(
        "/contas",
        json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 201


# --- Cenario 3: com token expirado ----------------------------------------


def test_rota_protegida_com_token_expirado_retorna_401(cliente):
    resposta = cliente.get("/contas/0", headers={"Authorization": f"Bearer {_token_expirado()}"})
    assert resposta.status_code == 401


def test_rota_protegida_com_token_invalido_retorna_401(cliente):
    resposta = cliente.get("/contas/0", headers={"Authorization": "Bearer token-invalido"})
    assert resposta.status_code == 401


# --- creditar-remoto usa um mecanismo diferente (service token) ----------


def test_creditar_remoto_sem_service_token_retorna_401(cliente):
    resposta = cliente.post("/contas/0/creditar-remoto", json={"valor": 10, "timestampLamport": 1, "origemAgencia": 1})
    assert resposta.status_code == 401


def test_creditar_remoto_com_jwt_de_usuario_nao_e_aceito(cliente):
    login = cliente.post("/auth/login", json={"usuario": "aluno", "senha": "senha123"})
    token = login.json()["access_token"]
    resposta = cliente.post(
        "/contas/0/creditar-remoto",
        json={"valor": 10, "timestampLamport": 1, "origemAgencia": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 401


def test_creditar_remoto_com_service_token_funciona(cliente):
    cliente.post(
        "/contas",
        json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 0},
        headers={"Authorization": f"Bearer {auth_service.criar_token('aluno')}"},
    )
    resposta = cliente.post(
        "/contas/0/creditar-remoto",
        json={"valor": 10, "timestampLamport": 1, "origemAgencia": 1},
        headers={"Authorization": f"Service {auth_service.SERVICE_TOKEN}"},
    )
    assert resposta.status_code == 200
