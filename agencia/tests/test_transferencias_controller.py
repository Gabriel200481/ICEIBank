import pytest
from fastapi.testclient import TestClient

from src.services import auth_service
from tests.rede_2pc import montar_agencias


@pytest.fixture
def agencias():
    apps, rede = montar_agencias()
    clientes = {i: TestClient(a) for i, a in apps.items()}
    for c in clientes.values():
        c.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    return apps, rede, clientes


def _conta(clientes, id_conta, saldo):
    clientes[id_conta % 3].post("/contas", json={"id": id_conta, "nomeAluno": "X", "saldoInicial": saldo})


def _saldo(clientes, id_conta):
    return clientes[id_conta % 3].get(f"/contas/{id_conta}").json()


def test_transferencia_entre_agencias_commit(agencias):
    _, _, c = agencias
    _conta(c, 0, 100)
    _conta(c, 1, 0)
    # a agencia 0 nao e a lider (2): encaminha o pedido
    r = c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 40})
    assert r.status_code == 200
    assert r.json()["resultado"] == "COMMIT" and "concluida" in r.json()["mensagem"]
    assert (_saldo(c, 0)["saldo"], _saldo(c, 0)["reservado"]) == (60, 0)
    assert (_saldo(c, 1)["saldo"], _saldo(c, 1)["reservado"]) == (40, 0)


def test_transferencia_mesma_agencia_participa_duas_vezes(agencias):
    _, _, c = agencias
    _conta(c, 0, 100)
    _conta(c, 3, 10)
    r = c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": 30})
    assert r.status_code == 200
    assert (_saldo(c, 0)["saldo"], _saldo(c, 3)["saldo"]) == (70, 40)


def test_saldo_insuficiente_aborta_sem_efeito_residual(agencias):
    _, _, c = agencias
    _conta(c, 0, 10)
    _conta(c, 1, 0)
    r = c[1].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 500})
    assert r.status_code == 422
    assert "Saldo insuficiente" in r.json()["detail"]
    assert (_saldo(c, 0)["saldo"], _saldo(c, 0)["reservado"], _saldo(c, 1)["saldo"]) == (10, 0, 0)


def test_conta_de_destino_inexistente_nao_deixa_debito_aplicado(agencias):
    """O caso em que, no Sprint 2, o dinheiro sumia."""
    _, _, c = agencias
    _conta(c, 0, 100)
    r = c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 99, "valor": 40})
    assert r.status_code == 422
    assert (_saldo(c, 0)["saldo"], _saldo(c, 0)["reservado"]) == (100, 0)


def test_conta_de_origem_inexistente_aborta(agencias):
    _, _, c = agencias
    _conta(c, 1, 0)
    assert c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 5}).status_code == 422


@pytest.mark.parametrize(
    "corpo",
    [
        {"idOrigem": 0, "idDestino": 0, "valor": 5},
        {"idOrigem": 0, "idDestino": 1, "valor": 0},
        {"idOrigem": 0, "idDestino": 1, "valor": -5},
    ],
)
def test_pedido_invalido_400(agencias, corpo):
    assert agencias[2][0].post("/transferencias", json=corpo).status_code == 400


def test_sem_lider_503(agencias):
    apps, _, c = agencias
    apps[0].state.bully._lider_atual = None
    assert c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 5}).status_code == 503


def test_transferencia_exige_jwt(agencias):
    _, _, c = agencias
    c[0].headers.pop("Authorization")
    assert c[0].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 5}).status_code == 401


def test_lider_coordena_diretamente(agencias):
    _, _, c = agencias
    _conta(c, 0, 100)
    _conta(c, 1, 0)
    assert c[2].post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 1}).status_code == 200


def test_coordenar_numa_agencia_que_nao_e_lider_409(agencias):
    _, _, c = agencias
    r = c[0].post(
        "/2pc/coordenar",
        json={"idOrigem": 0, "idDestino": 1, "valor": 1},
        headers={"x-token-interno": "token-de-teste"},
    )
    assert r.status_code == 409
