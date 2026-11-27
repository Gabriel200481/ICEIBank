"""Publica, em um topico SNS (na nuvem local, o LocalStack), o resultado de cada
transferencia decidida (Sprint 4, Parte F).

E uma notificacao "melhor esforco", FORA do caminho critico do 2PC: roda em
thread propria, com timeout curto, e nunca levanta excecao para o coordenador.
Se a nuvem estiver fora do ar a transferencia nao e afetada; so o comprovante
deixa de ser gerado.

So fica ativo se SNS_TOPIC_ARN estiver definido. O endpoint vem de
AWS_ENDPOINT_URL (ex.: http://localstack:4566), lido pelo proprio boto3.

shortcut: sem outbox - se a lider cair entre gravar a decisao e publicar, o
comprovante daquela transferencia nunca e gerado (ver RESPOSTAS.md, Parte F).
"""

import json
import threading
from datetime import datetime, timezone

from src import config


def _cliente_sns():
    import boto3  # import tardio: so quem usa a nuvem precisa do boto3
    from botocore.config import Config

    return boto3.client(
        "sns", config=Config(connect_timeout=1, read_timeout=2, retries={"max_attempts": 0})
    )


class EventosNuvem:
    def __init__(self, id_agencia, relogio, registro, topico=None, cliente=None) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.topico = config.SNS_TOPIC_ARN if topico is None else topico
        self._cliente = cliente

    def _publicar(self, evento: dict) -> None:
        try:
            if self._cliente is None:
                self._cliente = _cliente_sns()
            self._cliente.publish(TopicArn=self.topico, Message=json.dumps(evento))
            self.registro.registrar("NUVEM_EVENTO_PUBLICADO", self.relogio.evento_local(), {"txId": evento["txId"]})
        except Exception as erro:
            self.registro.registrar(
                "NUVEM_PUBLICACAO_FALHOU", self.relogio.evento_local(), {"txId": evento["txId"], "erro": type(erro).__name__}
            )

    def publicar_decisao(self, coord: dict) -> None:
        if not self.topico:
            return
        debito = next(p["operacao"] for p in coord["participantes"] if p["operacao"]["tipo"] == "DEBITO")
        credito = next(p["operacao"] for p in coord["participantes"] if p["operacao"]["tipo"] == "CREDITO")
        evento = {
            "txId": coord["txId"],
            "resultado": coord["decisao"],
            "idOrigem": debito["idConta"],
            "idDestino": credito["idConta"],
            "valor": debito["valor"],
            "coordenador": self.id_agencia,
            "decididaEm": datetime.now(timezone.utc).isoformat(),
        }
        threading.Thread(target=self._publicar, args=(evento,), daemon=True).start()
