"""Comunicacao indireta via RabbitMQ (Sprint 2).

Substitui a chamada REST direta do Sprint 1 entre agencias: em vez de uma
agencia chamar a outra pela rede, ela publica um evento numa exchange, e a
agencia de destino consome quando puder - mesmo que esteja fora do ar no
momento da publicacao (a mensagem fica retida na fila ate ser consumida).

Topologia: uma exchange "topic" compartilhada (iceibank.eventos), uma fila
por agencia (fila-agencia-<id>), ligada a exchange pela routing key
"agencia.<id>.creditar". So a fila daquela agencia recebe mensagens com
aquela routing key, mesmo a exchange sendo compartilhada por todas.
"""

import json
import os
import threading
from typing import Callable

import pika

EXCHANGE = "iceibank.eventos"


def _url() -> str:
    url = os.environ.get("RABBITMQ_URL")
    if not url:
        raise RuntimeError(
            "Defina a variavel de ambiente RABBITMQ_URL com a URL AMQP da sua "
            "instancia (CloudAMQP ou RabbitMQ local) antes de iniciar a agencia."
        )
    return url


def publicar(routing_key: str, mensagem: dict) -> None:
    conexao = pika.BlockingConnection(pika.URLParameters(_url()))
    try:
        canal = conexao.channel()
        canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        canal.basic_publish(
            exchange=EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(mensagem).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),  # mensagem persistente
        )
    finally:
        conexao.close()


def assinar(id_agencia: int, ao_receber_mensagem: Callable[[dict], None]) -> threading.Thread:
    """Inicia, numa thread dedicada, o consumo continuo da fila da agencia.

    Roda em paralelo ao servidor HTTP (FastAPI/Uvicorn so atende requisicoes
    na thread principal/threadpool - o consumo de mensagens precisa da sua
    propria thread, ja que canal.start_consuming() bloqueia indefinidamente).
    """

    def _consumir() -> None:
        conexao = pika.BlockingConnection(pika.URLParameters(_url()))
        canal = conexao.channel()
        canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

        nome_fila = f"fila-agencia-{id_agencia}"
        canal.queue_declare(queue=nome_fila, durable=True)
        canal.queue_bind(exchange=EXCHANGE, queue=nome_fila, routing_key=f"agencia.{id_agencia}.creditar")

        def _callback(ch, method, _properties, body) -> None:
            mensagem = json.loads(body.decode("utf-8"))
            ao_receber_mensagem(mensagem)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        canal.basic_consume(queue=nome_fila, on_message_callback=_callback)
        canal.start_consuming()

    thread = threading.Thread(target=_consumir, daemon=True, name=f"consumidor-agencia-{id_agencia}")
    thread.start()
    return thread
