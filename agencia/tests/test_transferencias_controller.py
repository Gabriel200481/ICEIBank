import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.controllers import transferencias_controller
from src.services import auth_service


def _criar_cliente(tmp_path, id_agencia):
    app = criar_app(id_agencia=id_agencia, iniciar_consumidor=False)
    app.state.registro.caminho_arquivo = tmp_path / f"eventos-agencia-{id_agencia}.jsonl"
    cliente = TestClient(app)
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


def test_transferencia_entre_agencias_publica_mensagem_e_destino_processa(tmp_path, monkeypatch):
    app_origem, cliente_origem = _criar_cliente(tmp_path, id_agencia=0)
    app_destino, cliente_destino = _criar_cliente(tmp_path, id_agencia=1)

    cliente_origem.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})
    cliente_destino.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})

    def fake_publicar(routing_key, mensagem):
        # Simula o papel do broker: entrega a mensagem direto para o
        # consumidor da agencia de destino, sem precisar de um RabbitMQ
        # real neste teste (validado separadamente em test_mensageria.py).
        assert routing_key == "agencia.1.creditar"
        app_destino.state.processar_credito_recebido(mensagem)

    monkeypatch.setattr(transferencias_controller.mensageria, "publicar", fake_publicar)

    resposta = cliente_origem.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 40})

    assert resposta.status_code == 200
    assert "assincrona" in resposta.json()["mensagem"]
    assert cliente_origem.get("/contas/0").json()["saldo"] == 60
    assert cliente_destino.get("/contas/1").json()["saldo"] == 40

    assert app_origem.state.relogio.vetor == [3, 0, 0]
    assert app_destino.state.relogio.vetor == [3, 2, 0]
    # regra 3 do relogio vetorial: quem recebe domina quem enviou em toda
    # posicao (relacao causal real, nao so timestamps diferentes).
    assert all(app_origem.state.relogio.vetor[i] <= app_destino.state.relogio.vetor[i] for i in range(3))


def test_transferencia_entre_agencias_responde_200_mesmo_sem_ninguem_consumindo(tmp_path, monkeypatch):
    """Diferenca central em relacao ao Sprint 1: a resposta HTTP nao depende
    mais de a agencia de destino estar no ar. O debito e aplicado e a
    mensagem e publicada de qualquer forma - quem consome (ou nao, ainda)
    e assunto da fila, nao da requisicao HTTP."""
    app_origem, cliente_origem = _criar_cliente(tmp_path, id_agencia=0)
    cliente_origem.post("/contas", json={"id": 0, "nomeAluno": "Ana", "saldoInicial": 100})

    mensagens_publicadas = []
    monkeypatch.setattr(
        transferencias_controller.mensageria,
        "publicar",
        lambda routing_key, mensagem: mensagens_publicadas.append((routing_key, mensagem)),
    )

    resposta = cliente_origem.post("/transferencias", json={"idOrigem": 0, "idDestino": 1, "valor": 40})

    assert resposta.status_code == 200
    assert cliente_origem.get("/contas/0").json()["saldo"] == 60
    assert len(mensagens_publicadas) == 1
    assert mensagens_publicadas[0][0] == "agencia.1.creditar"
    assert mensagens_publicadas[0][1]["idConta"] == 1
    assert mensagens_publicadas[0][1]["valor"] == 40


def test_processar_credito_recebido_usa_ao_receber_do_relogio_vetorial(tmp_path):
    app_destino, cliente_destino = _criar_cliente(tmp_path, id_agencia=1)
    cliente_destino.post("/contas", json={"id": 1, "nomeAluno": "Bia", "saldoInicial": 0})

    app_destino.state.relogio.vetor = [10, 5, 0]  # agencia de destino "adiantada"

    app_destino.state.processar_credito_recebido(
        {"idConta": 1, "valor": 50, "vetorEnvio": [3, 0, 0], "origemAgencia": 0}
    )

    assert cliente_destino.get("/contas/1").json()["saldo"] == 50
    # max([10,5,0], [3,0,0]) = [10,5,0], depois incrementa a propria posicao (1) -> [10,6,0]
    assert app_destino.state.relogio.vetor == [10, 6, 0]


def test_processar_credito_recebido_com_conta_inexistente_registra_falha(tmp_path):
    """Reproduz a limitacao conhecida deste sprint (secao 2 do roteiro): se a
    conta nao existe quando a mensagem chega (ex.: a agencia reiniciou e
    perdeu o estado em memoria), o credito nao e aplicado silenciosamente -
    fica registrado no log como CREDITO_REMOTO_FALHOU."""
    app_destino, _ = _criar_cliente(tmp_path, id_agencia=1)

    app_destino.state.processar_credito_recebido(
        {"idConta": 99, "valor": 50, "vetorEnvio": [1, 0, 0], "origemAgencia": 0}
    )

    linhas = app_destino.state.registro.caminho_arquivo.read_text(encoding="utf-8").strip().splitlines()
    assert any('"CREDITO_REMOTO_FALHOU"' in linha for linha in linhas)
