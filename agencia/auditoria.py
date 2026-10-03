"""Funcionalidade adicional (Sprint 2, secao 2.1): fila de auditoria.

Um consumidor extra, independente das 3 agencias, que escuta TODOS os
creditos publicados por qualquer agencia - ligando sua fila a exchange com
a routing key coringa "agencia.*.creditar" - e mantem um log central de
auditoria (agencia/data/auditoria.jsonl). Util para observar o sistema de
fora, sem precisar entrar em cada agencia individualmente (ex.: um
dashboard de compliance, ou so para depurar o fluxo de mensagens).

Diferenca em relacao as filas das agencias: cada fila de agencia se liga
com a routing key EXATA dela ("agencia.0.creditar", por exemplo), entao so
recebe mensagens destinadas aquela agencia especifica. Essa fila de
auditoria usa um padrao ("agencia.*.creditar") para capturar uma copia de
TODAS as mensagens de credito, de qualquer agencia - uma exchange topic
entrega a mesma mensagem para cada fila cuja routing key bate com ela,
entao a agencia de destino recebe sua copia normalmente e a auditoria
recebe a dela, sem interferir uma na outra.

Uso: roda como um processo separado, em paralelo as 3 agencias.

    python auditoria.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pika

from src.services.mensageria import EXCHANGE, url_rabbitmq

PASTA_DADOS = Path(__file__).resolve().parent / "data"
CAMINHO_AUDITORIA = PASTA_DADOS / "auditoria.jsonl"
FILA_AUDITORIA = "fila-auditoria"
ROUTING_KEY_CORINGA = "agencia.*.creditar"


def registrar(mensagem: dict, pasta_dados: Path = PASTA_DADOS) -> dict:
    pasta_dados.mkdir(parents=True, exist_ok=True)
    evento = {
        "horaAuditoria": datetime.now(timezone.utc).isoformat(),
        "mensagem": mensagem,
    }
    caminho = pasta_dados / "auditoria.jsonl"
    with open(caminho, "a", encoding="utf-8", newline="") as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    print(f"[AUDITORIA] credito capturado: {mensagem}")
    return evento


def main() -> None:
    conexao = pika.BlockingConnection(pika.URLParameters(url_rabbitmq()))
    canal = conexao.channel()
    canal.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    canal.queue_declare(queue=FILA_AUDITORIA, durable=True)
    canal.queue_bind(exchange=EXCHANGE, queue=FILA_AUDITORIA, routing_key=ROUTING_KEY_CORINGA)

    def _callback(ch, method, _properties, body) -> None:
        mensagem = json.loads(body.decode("utf-8"))
        registrar(mensagem)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    canal.basic_consume(queue=FILA_AUDITORIA, on_message_callback=_callback)
    print(f"[AUDITORIA] escutando '{ROUTING_KEY_CORINGA}' na exchange '{EXCHANGE}' - Ctrl+C para sair")
    try:
        canal.start_consuming()
    except KeyboardInterrupt:
        canal.stop_consuming()
    finally:
        conexao.close()


if __name__ == "__main__":
    main()
