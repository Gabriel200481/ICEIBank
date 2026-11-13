import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services import auth_service
from src.services.extrato import montar_extrato


@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=0, iniciar_consumidor=False, iniciar_bully=False)
    app.state.registro.caminho_arquivo = tmp_path / "eventos.jsonl"
    cliente = TestClient(app)
    cliente.headers.update({"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    return cliente


def test_conta_sem_movimento_alem_da_abertura(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    corpo = cliente.get("/contas/0/extrato").json()
    assert corpo["saldoAtual"] == 100
    assert [m["descricao"] for m in corpo["movimentos"]] == ["Abertura de conta"]


def test_extrato_lista_deposito_saque_em_ordem(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente.post("/contas/0/depositar", json={"valor": 50})
    cliente.post("/contas/0/sacar", json={"valor": 30})
    valores = [m["valor"] for m in cliente.get("/contas/0/extrato").json()["movimentos"]]
    assert valores == [100, 50, -30]
    assert sum(valores) == cliente.get("/contas/0").json()["saldo"]


def test_transferencia_local_aparece_nas_duas_contas(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente.post("/contas", json={"id": 3, "nomeAluno": "Caio", "saldoInicial": 0})
    cliente.post("/transferencias", json={"idOrigem": 0, "idDestino": 3, "valor": 40})
    origem = cliente.get("/contas/0/extrato").json()["movimentos"]
    destino = cliente.get("/contas/3/extrato").json()["movimentos"]
    assert origem[-1]["valor"] == -40 and "enviada" in origem[-1]["descricao"]
    assert destino[-1]["valor"] == 40 and "recebida" in destino[-1]["descricao"]
    # o debito da conta 0 nao vaza para o extrato da conta 3 e vice-versa
    assert all("enviada" not in m["descricao"] for m in destino)


def test_operacao_sincronizada_aparece_e_conflito_nao(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente.post("/sincronizar", json={"idOperacao": "a", "tipo": "DEPOSITO", "idConta": 0, "valor": 10, "vetorBase": [1, 0, 0]})
    cliente.post("/sincronizar", json={"idOperacao": "b", "tipo": "SAQUE", "idConta": 0, "valor": 5, "vetorBase": [0, 0, 0]})  # conflito
    movimentos = cliente.get("/contas/0/extrato").json()["movimentos"]
    assert [m["valor"] for m in movimentos] == [100, 10]
    assert "sincronizado" in movimentos[1]["descricao"]


def test_extrato_de_conta_inexistente_404(cliente):
    assert cliente.get("/contas/99/extrato").status_code == 404


def test_extrato_exige_token(cliente):
    cliente.headers.pop("Authorization")
    assert cliente.get("/contas/0/extrato").status_code == 401


def test_extrato_nao_mistura_contas(cliente):
    cliente.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 1})
    cliente.post("/contas", json={"id": 3, "nomeAluno": "Caio", "saldoInicial": 2})
    cliente.post("/contas/3/depositar", json={"valor": 7})
    assert [m["valor"] for m in cliente.get("/contas/0/extrato").json()["movimentos"]] == [1]


def test_montar_extrato_ignora_eventos_desconhecidos():
    eventos = [{"tipo": "ELEICAO_INICIADA", "detalhes": {}, "horaParede": "x", "timestampVetorial": [0, 0, 0]}]
    assert montar_extrato(eventos, 0) == []


def test_registro_ler_sem_arquivo_retorna_vazio(tmp_path):
    from src.services.event_log import RegistroEventos

    assert RegistroEventos("x", pasta_dados=str(tmp_path)).ler() == []
