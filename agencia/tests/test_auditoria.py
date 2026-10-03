import json
import os
import time
import uuid

import pika
import pytest

from auditoria import registrar
from src.services import mensageria


def test_registrar_grava_evento_com_hora_de_auditoria(tmp_path):
    mensagem = {"idConta": 1, "valor": 40.0, "vetorEnvio": [3, 0, 0], "origemAgencia": 0}

    evento = registrar(mensagem, pasta_dados=tmp_path)

    assert evento["mensagem"] == mensagem
    assert "horaAuditoria" in evento

    caminho = tmp_path / "auditoria.jsonl"
    assert caminho.exists()
    linha = json.loads(caminho.read_text(encoding="utf-8").strip().splitlines()[0])
    assert linha["mensagem"]["idConta"] == 1


def test_registrar_multiplos_eventos_faz_append(tmp_path):
    registrar({"idConta": 1, "valor": 10.0}, pasta_dados=tmp_path)
    registrar({"idConta": 2, "valor": 20.0}, pasta_dados=tmp_path)

    linhas = (tmp_path / "auditoria.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2


@pytest.mark.skipif(
    not os.environ.get("RABBITMQ_URL"),
    reason="RABBITMQ_URL nao definida - teste de integracao do RabbitMQ pulado",
)
def test_fila_de_auditoria_com_routing_key_coringa_captura_creditos_de_qualquer_agencia():
    """Valida o ponto central da funcionalidade adicional: uma fila ligada
    com o padrao "agencia.*.creditar" recebe uma copia de mensagens
    publicadas para QUALQUER agencia - diferente das filas normais, que so
    ouvem a propria routing key exata.
    """
    sufixo = uuid.uuid4().hex[:8]
    fila_auditoria = f"fila-auditoria-teste-{sufixo}"

    conexao = pika.BlockingConnection(pika.URLParameters(mensageria.url_rabbitmq()))
    canal = conexao.channel()
    canal.exchange_declare(exchange=mensageria.EXCHANGE, exchange_type="topic", durable=True)
    canal.queue_declare(queue=fila_auditoria, durable=True)
    canal.queue_bind(exchange=mensageria.EXCHANGE, queue=fila_auditoria, routing_key=f"agencia.*.creditar.{sufixo}")
    conexao.close()

    recebidas = []

    def _consumir():
        conexao2 = pika.BlockingConnection(pika.URLParameters(mensageria.url_rabbitmq()))
        canal2 = conexao2.channel()

        def _callback(ch, method, _properties, body):
            recebidas.append(json.loads(body.decode("utf-8")))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        canal2.basic_consume(queue=fila_auditoria, on_message_callback=_callback)
        canal2.start_consuming()

    import threading

    threading.Thread(target=_consumir, daemon=True).start()

    # Publica para duas "agencias" diferentes (routing keys diferentes, mas
    # ambas batem no padrao coringa da fila de auditoria).
    mensageria.publicar(f"agencia.0.creditar.{sufixo}", {"idConta": 1, "valor": 10})
    mensageria.publicar(f"agencia.1.creditar.{sufixo}", {"idConta": 2, "valor": 20})

    limite = time.monotonic() + 5
    while len(recebidas) < 2 and time.monotonic() < limite:
        time.sleep(0.1)

    assert len(recebidas) == 2
    assert {m["idConta"] for m in recebidas} == {1, 2}
