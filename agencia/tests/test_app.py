from fastapi.testclient import TestClient

from src.app import app

cliente = TestClient(app)


def test_raiz_responde_ok():
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
