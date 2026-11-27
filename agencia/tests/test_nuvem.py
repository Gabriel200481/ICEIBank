"""Parte F: publicacao no SNS (agencia) e as duas funcoes Lambda."""

import importlib.util
import json
import threading
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from src.services.armazenamento import EstadoDuravel
from src.services.event_log import RegistroEventos
from src.services.eventos_nuvem import EventosNuvem
from src.services.vector_clock import RelogioVetorial

RAIZ = Path(__file__).resolve().parents[2] / "serverless"
COORD = {
    "txId": "tx-1",
    "decisao": "COMMIT",
    "participantes": [
        {"operacao": {"tipo": "DEBITO", "idConta": 0, "valor": 12.5}},
        {"operacao": {"tipo": "CREDITO", "idConta": 1, "valor": 12.5}},
    ],
}


class SnsFalso:
    def __init__(self, erro=None):
        self.publicacoes, self.erro, self.feito = [], erro, threading.Event()

    def publish(self, **kwargs):
        self.feito.set()
        if self.erro:
            raise self.erro
        self.publicacoes.append(kwargs)


def _eventos(tmp_path, topico, cliente):
    registro = RegistroEventos("agencia-2", pasta_dados=str(tmp_path))
    return EventosNuvem(2, RelogioVetorial(2, 3), registro, topico=topico, cliente=cliente), registro


def _aguardar_log(registro, tipo):
    for _ in range(100):
        if any(e["tipo"] == tipo for e in registro.ler()):
            return True
        threading.Event().wait(0.02)
    return False


def test_publica_o_resultado_da_transferencia(tmp_path):
    sns = SnsFalso()
    nuvem, registro = _eventos(tmp_path, "arn:topico", sns)
    nuvem.publicar_decisao(COORD)
    assert _aguardar_log(registro, "NUVEM_EVENTO_PUBLICADO")
    corpo = json.loads(sns.publicacoes[0]["Message"])
    assert sns.publicacoes[0]["TopicArn"] == "arn:topico"
    assert (corpo["txId"], corpo["resultado"], corpo["idOrigem"], corpo["idDestino"], corpo["valor"]) == ("tx-1", "COMMIT", 0, 1, 12.5)


def test_nuvem_fora_do_ar_nao_levanta_excecao_e_registra_a_falha(tmp_path):
    nuvem, registro = _eventos(tmp_path, "arn:topico", SnsFalso(erro=ConnectionError("fora")))
    nuvem.publicar_decisao(COORD)  # nao levanta: fora do caminho critico
    assert _aguardar_log(registro, "NUVEM_PUBLICACAO_FALHOU")


def test_sem_topico_configurado_nao_faz_nada(tmp_path):
    sns = SnsFalso()
    nuvem, _ = _eventos(tmp_path, "", sns)
    nuvem.publicar_decisao(COORD)
    assert not sns.feito.wait(0.1)


# ---- Lambdas ----


def _carregar(nome, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    spec = importlib.util.spec_from_file_location(f"lambda_{nome}", RAIZ / nome / "lambda_function.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class S3Falso:
    def __init__(self):
        self.objetos = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objetos[Key] = Body

    def get_object(self, Bucket, Key):
        if Key not in self.objetos:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        corpo = self.objetos[Key]
        return {"Body": type("B", (), {"read": lambda self: corpo.encode()})()}


class TabelaFalsa:
    def __init__(self):
        self.itens = {}

    def put_item(self, Item, ConditionExpression):
        # o DynamoDB real recusa float: o serializador do boto3 tambem
        from boto3.dynamodb.types import TypeSerializer

        TypeSerializer().serialize(Item)
        if Item["txId"] in self.itens:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.itens[Item["txId"]] = Item

    def get_item(self, Key):
        item = self.itens.get(Key["txId"])
        return {"Item": item} if item else {}


def _registro_sqs(message_id, evento, envelope=False):
    corpo = json.dumps({"Message": json.dumps(evento)} if envelope else evento)
    return {"messageId": message_id, "body": corpo}


EVENTO = {"txId": "tx-1", "resultado": "COMMIT", "idOrigem": 0, "idDestino": 1, "valor": 12.5}


@pytest.fixture
def gerar(monkeypatch):
    m = _carregar("gerar-comprovante", monkeypatch)
    m.s3, m.tabela = S3Falso(), TabelaFalsa()
    return m


def test_gerar_comprovante_grava_no_s3_e_no_dynamo(gerar):
    r = gerar.handler({"Records": [_registro_sqs("m1", EVENTO)]})
    assert r == {"batchItemFailures": []}
    assert json.loads(gerar.s3.objetos["comprovantes/tx-1.json"])["mensagem"] == "Transferencia concluida."
    assert gerar.tabela.itens["tx-1"]["valor"] == 12.5  # Decimal == float


def test_gerar_comprovante_aceita_envelope_do_sns_e_abort(gerar):
    abort = {**EVENTO, "txId": "tx-2", "resultado": "ABORT"}
    gerar.handler({"Records": [_registro_sqs("m1", abort, envelope=True)]})
    assert json.loads(gerar.s3.objetos["comprovantes/tx-2.json"])["mensagem"] == "Transferencia nao realizada."


def test_gerar_comprovante_e_idempotente_na_reentrega(gerar):
    registro = _registro_sqs("m1", EVENTO)
    gerar.handler({"Records": [registro]})
    primeiro = gerar.tabela.itens["tx-1"]["emitidoEm"]
    r = gerar.handler({"Records": [registro]})  # a mesma mensagem chega de novo
    assert r == {"batchItemFailures": []}
    assert gerar.tabela.itens["tx-1"]["emitidoEm"] == primeiro and len(gerar.tabela.itens) == 1


def test_so_a_mensagem_que_falha_volta_para_a_fila(gerar):
    lote = {"Records": [_registro_sqs("boa", EVENTO), {"messageId": "ruim", "body": "isto nao e json"}]}
    assert gerar.handler(lote) == {"batchItemFailures": [{"itemIdentifier": "ruim"}]}
    assert "tx-1" in gerar.tabela.itens  # a boa foi processada


def test_consultar_comprovante(gerar, monkeypatch):
    gerar.handler({"Records": [_registro_sqs("m1", EVENTO)]})
    consulta = _carregar("consultar-comprovante", monkeypatch)
    consulta.s3, consulta.tabela = gerar.s3, gerar.tabela

    ok = consulta.handler({"pathParameters": {"txId": "tx-1"}})
    assert ok["statusCode"] == 200 and json.loads(ok["body"])["resultado"] == "COMMIT"
    assert consulta.handler({"pathParameters": {"txId": "nao-existe"}})["statusCode"] == 404
    assert consulta.handler({"pathParameters": None})["statusCode"] == 400


def test_consultar_devolve_o_resumo_do_dynamo_se_o_objeto_s3_faltar(gerar, monkeypatch):
    gerar.handler({"Records": [_registro_sqs("m1", EVENTO)]})
    consulta = _carregar("consultar-comprovante", monkeypatch)
    consulta.s3, consulta.tabela = S3Falso(), gerar.tabela
    r = consulta.handler({"pathParameters": {"txId": "tx-1"}})
    assert r["statusCode"] == 200 and json.loads(r["body"])["valor"] == 12.5
