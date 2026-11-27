"""Funcao Lambda acionada por uma fila SQS (Sprint 4, Parte F).

Cada mensagem e o resultado de uma transferencia (publicado pela agencia
coordenadora via SNS). Para cada uma:
  1. grava o comprovante (JSON) em um bucket S3;
  2. registra um indice no DynamoDB, com chave txId.
SQS entrega "pelo menos uma vez", entao a funcao precisa ser IDEMPOTENTE.
"""

import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = os.environ.get("BUCKET", "iceibank-comprovantes")
TABELA = os.environ.get("TABELA", "comprovantes")
# AWS_ENDPOINT_URL (definido no LocalStack, ausente na AWS real) e lido pelo proprio boto3;
# no S3 local o endereco precisa ser "path style".
_s3_config = Config(s3={"addressing_style": "path"}) if os.environ.get("AWS_ENDPOINT_URL") else None

s3 = boto3.client("s3", config=_s3_config)
tabela = boto3.resource("dynamodb").Table(TABELA)


def ler_evento(corpo: str) -> dict:
    externo = json.loads(corpo)
    # Sem "raw message delivery", o SNS embrulha o evento em um envelope com o campo Message.
    return json.loads(externo["Message"]) if "Message" in externo else externo


def handler(event, context=None):
    falhas = []
    for registro in event["Records"]:
        try:
            ev = ler_evento(registro["body"])
            emitido_em = datetime.now(timezone.utc).isoformat()
            comprovante = {
                **ev,
                "emitidoEm": emitido_em,
                "mensagem": "Transferencia concluida." if ev["resultado"] == "COMMIT" else "Transferencia nao realizada.",
            }
            s3.put_object(
                Bucket=BUCKET,
                Key=f"comprovantes/{ev['txId']}.json",
                Body=json.dumps(comprovante),
                ContentType="application/json",
            )
            item = {
                "txId": ev["txId"],
                "resultado": ev["resultado"],
                "valor": ev["valor"],
                "idOrigem": ev["idOrigem"],
                "idDestino": ev["idDestino"],
                "emitidoEm": emitido_em,
            }
            try:
                tabela.put_item(
                    # o DynamoDB nao aceita float: converte para Decimal
                    Item=json.loads(json.dumps(item), parse_float=Decimal),
                    ConditionExpression="attribute_not_exists(txId)",  # reentrega da mesma mensagem: ignora
                )
            except ClientError as erro:
                if erro.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
        except Exception as erro:
            print("falha ao processar", registro.get("messageId"), repr(erro))
            falhas.append({"itemIdentifier": registro["messageId"]})  # so esta mensagem volta para a fila
    return {"batchItemFailures": falhas}
