"""Segunda funcao Lambda (Sprint 4, Parte F): GET /comprovantes/{txId}.

Exposta por um API Gateway. Le o indice do DynamoDB e devolve o comprovante
completo do S3; 404 se o txId nao existe (ainda: o comprovante e gerado de
forma assincrona, entao logo apos a transferencia ele pode nao existir).
"""

import json
import os
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = os.environ.get("BUCKET", "iceibank-comprovantes")
TABELA = os.environ.get("TABELA", "comprovantes")
_s3_config = Config(s3={"addressing_style": "path"}) if os.environ.get("AWS_ENDPOINT_URL") else None

s3 = boto3.client("s3", config=_s3_config)
tabela = boto3.resource("dynamodb").Table(TABELA)


def _resposta(status: int, corpo: dict) -> dict:
    # default: o DynamoDB devolve numeros como Decimal, que o json nao serializa
    texto = json.dumps(corpo, default=lambda x: float(x) if isinstance(x, Decimal) else str(x))
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": texto}


def handler(event, context=None):
    tx_id = ((event or {}).get("pathParameters") or {}).get("txId")
    if not tx_id:
        return _resposta(400, {"erro": "Informe o txId."})

    item = tabela.get_item(Key={"txId": tx_id}).get("Item")
    if not item:
        return _resposta(404, {"erro": "Comprovante nao encontrado.", "txId": tx_id})
    try:
        objeto = s3.get_object(Bucket=BUCKET, Key=f"comprovantes/{tx_id}.json")
        return _resposta(200, json.loads(objeto["Body"].read()))
    except ClientError:
        return _resposta(200, item)  # indice sem o objeto: devolve ao menos o resumo
