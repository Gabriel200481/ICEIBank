"""Testes de integracao reais contra um broker RabbitMQ - precisam de
RABBITMQ_URL apontando para uma instancia de verdade (CloudAMQP ou
`docker run rabbitmq:3-management`, ver README). Validam publicar()/assinar()
end-to-end, diferente dos testes de controller (que simulam a entrega via
monkeypatch para rodar rapido e sem depender de infraestrutura externa).
"""

import os
import time
import uuid

import pika
import pytest

from src.services import mensageria

pytestmark = pytest.mark.skipif(
    not os.environ.get("RABBITMQ_URL"),
    reason="RABBITMQ_URL nao definida - testes de integracao do RabbitMQ pulados",
)


def _declarar_fila_sem_consumir(id_agencia: int) -> None:
    """Simula a agencia ja ter rodado antes (fila durable ja existe e esta
    ligada a exchange) sem deixar nenhum consumidor ativo - e exatamente
    esse estado (fila existe, ninguem consumindo) que faz uma mensagem
    publicada "sobreviver" ate alguem voltar a consumir.
    """
    conexao = pika.BlockingConnection(pika.URLParameters(mensageria.url_rabbitmq()))
    canal = conexao.channel()
    canal.exchange_declare(exchange=mensageria.EXCHANGE, exchange_type="topic", durable=True)
    nome_fila = f"fila-agencia-{id_agencia}"
    canal.queue_declare(queue=nome_fila, durable=True)
    canal.queue_bind(exchange=mensageria.EXCHANGE, queue=nome_fila, routing_key=f"agencia.{id_agencia}.creditar")
    conexao.close()


def test_publicar_e_assinar_entregam_mensagem_de_verdade():
    id_agencia = int(uuid.uuid4().int % 100000)  # fila/routing key isoladas deste teste
    recebidas = []

    mensageria.assinar(id_agencia, recebidas.append)

    mensagem = {"idConta": 1, "valor": 40.0, "vetorEnvio": [3, 0, 0], "origemAgencia": 0}
    mensageria.publicar(f"agencia.{id_agencia}.creditar", mensagem)

    limite = time.monotonic() + 5
    while not recebidas and time.monotonic() < limite:
        time.sleep(0.1)

    assert recebidas == [mensagem]


def test_mensagem_publicada_sem_consumidor_ativo_nao_se_perde():
    """Base do teste de resiliencia (Parte C, tarefa 3-4 do roteiro): a fila
    da agencia ja existe (ela ja rodou antes), mas ninguem esta consumindo
    agora - a mensagem publicada fica retida ate alguem voltar a consumir.
    """
    id_agencia = int(uuid.uuid4().int % 100000)
    mensagem = {"idConta": 2, "valor": 15.0, "vetorEnvio": [1, 0, 0], "origemAgencia": 1}

    _declarar_fila_sem_consumir(id_agencia)
    mensageria.publicar(f"agencia.{id_agencia}.creditar", mensagem)  # publicada "com a agencia fora do ar"

    recebidas = []
    mensageria.assinar(id_agencia, recebidas.append)  # agencia "volta" e passa a consumir

    limite = time.monotonic() + 5
    while not recebidas and time.monotonic() < limite:
        time.sleep(0.1)

    assert recebidas == [mensagem]
