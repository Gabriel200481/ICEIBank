import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services import auth_service
from src.services.vector_clock import comparar_vetores


@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=0, iniciar_consumidor=False, iniciar_bully=False)
    app.state.registro.caminho_arquivo = tmp_path / "eventos.jsonl"
    cliente = TestClient(app)
    cliente.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    return cliente


def op(id_operacao="op-1", tipo="DEPOSITO", valor=10, base=None, conta=0):
    return {"idOperacao": id_operacao, "tipo": tipo, "idConta": conta, "valor": valor, "vetorBase": base or [1, 0, 0]}


def test_comparar_vetores_e_funcao_pura_reutilizada_do_mesclar_logs():
    import mesclar_logs

    assert mesclar_logs.comparar_vetores is comparar_vetores
    assert comparar_vetores([1, 0, 0], [1, 0, 0]) == "IGUAIS"


def test_conta_expoe_versao_vetorial(cliente):
    assert cliente.get("/contas/0").json()["versao"] == [1, 0, 0]


def test_deposito_e_saque_atualizam_a_versao(cliente):
    cliente.post("/contas/0/depositar", json={"valor": 1})
    assert cliente.get("/contas/0").json()["versao"] == [2, 0, 0]
    cliente.post("/contas/0/sacar", json={"valor": 1})
    assert cliente.get("/contas/0").json()["versao"] == [3, 0, 0]


def test_caminho_feliz_aplica_deposito_e_avanca_versao(cliente):
    r = cliente.post("/sincronizar", json=op(base=[1, 0, 0]))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["status"] == "APLICADA"
    assert corpo["conta"]["saldo"] == 110
    assert comparar_vetores([1, 0, 0], corpo["conta"]["versao"]) == "ANTES"


def test_caminho_feliz_saque(cliente):
    r = cliente.post("/sincronizar", json=op(tipo="SAQUE", valor=40))
    assert r.status_code == 200 and r.json()["conta"]["saldo"] == 60


def test_operacoes_encadeadas_usando_a_versao_devolvida(cliente):
    v1 = cliente.post("/sincronizar", json=op("a", valor=10)).json()["conta"]["versao"]
    r2 = cliente.post("/sincronizar", json=op("b", valor=5, base=v1))
    assert r2.status_code == 200 and r2.json()["conta"]["saldo"] == 115


def test_conflito_quando_servidor_evoluiu_alem_do_cliente_ANTES(cliente):
    cliente.post("/contas/0/depositar", json={"valor": 50})  # versao [2,0,0]
    r = cliente.post("/sincronizar", json=op(base=[1, 0, 0]))
    assert r.status_code == 409
    corpo = r.json()
    assert corpo["status"] == "CONFLITO" and corpo["relacao"] == "ANTES"
    assert corpo["conta"]["saldo"] == 150  # estado do servidor, operacao NAO aplicada
    assert corpo["versaoServidor"] == [2, 0, 0]


def test_conflito_concorrente(cliente):
    # Cliente viu [1,0,2] (uma mudanca vinda da agencia 2); o servidor so tem [1,0,0] + local.
    cliente.post("/contas/0/depositar", json={"valor": 1})  # versao [2,0,0]
    r = cliente.post("/sincronizar", json=op(base=[1, 0, 2]))
    assert r.status_code == 409 and r.json()["relacao"] == "CONCORRENTES"


def test_conflito_nao_altera_saldo(cliente):
    cliente.post("/contas/0/depositar", json={"valor": 50})
    cliente.post("/sincronizar", json=op(base=[1, 0, 0]))
    assert cliente.get("/contas/0").json()["saldo"] == 150


def test_reenvio_da_mesma_operacao_e_idempotente(cliente):
    cliente.post("/sincronizar", json=op("x", valor=10))
    r = cliente.post("/sincronizar", json=op("x", valor=10))
    assert r.status_code == 200 and r.json()["status"] == "JA_APLICADA"
    assert cliente.get("/contas/0").json()["saldo"] == 110


def test_conta_inexistente_retorna_404(cliente):
    assert cliente.post("/sincronizar", json=op(conta=99)).status_code == 404


def test_saldo_insuficiente_retorna_400_sem_aplicar(cliente):
    r = cliente.post("/sincronizar", json=op(tipo="SAQUE", valor=500))
    assert r.status_code == 400
    assert cliente.get("/contas/0").json()["saldo"] == 100


def test_sem_token_retorna_401(cliente):
    cliente.headers.pop("Authorization")
    assert cliente.post("/sincronizar", json=op()).status_code == 401


def test_vetor_com_tamanho_errado_retorna_400(cliente):
    assert cliente.post("/sincronizar", json=op(base=[1, 0])).status_code == 400


@pytest.mark.parametrize("campo,valor", [("tipo", "TRANSFERENCIA"), ("valor", -5), ("valor", 0), ("idOperacao", "")])
def test_corpo_invalido_retorna_422(cliente, campo, valor):
    corpo = op()
    corpo[campo] = valor
    assert cliente.post("/sincronizar", json=corpo).status_code == 422


def test_eventos_sync_sao_registrados(cliente, tmp_path):
    cliente.post("/sincronizar", json=op("ok"))
    cliente.post("/sincronizar", json=op("velha", base=[0, 0, 0]))
    log = (tmp_path / "eventos.jsonl").read_text(encoding="utf-8")
    assert "SYNC_APLICADO" in log and "SYNC_CONFLITO" in log
