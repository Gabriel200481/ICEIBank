"""Papel de COORDENADOR no 2PC (Sprint 4, Parte C): a lider eleita pelo Bully.

Pontos criticos:
- a decisao so vale depois de gravada em disco (o "ponto sem volta");
- COMMIT so se TODOS votaram SIM; timeout conta como NAO;
- a decisao e reentregue periodicamente ate cada participante confirmar;
- aborto presumido: transacao que ficou na fase 1 quando a agencia caiu vira ABORT.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from src import config
from src.services import cliente_interno
from src.services.falhas import falhar


class Coordenador:
    def __init__(self, id_agencia, relogio, registro, estado, eventos_nuvem=None, cliente=cliente_interno) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.estado = estado
        self.eventos_nuvem = eventos_nuvem
        self.cliente = cliente
        self._reentregando = threading.Lock()

    def _pedir_voto(self, tx_id: str, p: dict) -> None:
        try:
            vetor_envio = self.relogio.ao_enviar()
            self.registro.registrar(
                "2PC_PREPARAR_ENVIADO", vetor_envio, {"txId": tx_id, "para": p["agencia"], "operacao": p["operacao"]}
            )
            resp = self.cliente.post(
                f"{config.url_da_agencia(p['agencia'])}/2pc/preparar",
                {"txId": tx_id, "operacao": p["operacao"], "coordenador": self.id_agencia, "vetorEnvio": vetor_envio},
                timeout=config.TIMEOUT_2PC,
            )
            self.relogio.ao_receber(resp["vetorEnvio"])
            p["voto"] = resp["voto"]
            p["motivo"] = resp.get("motivo")
        except Exception:
            # sem resposta dentro do prazo conta como voto NAO
            p["voto"] = "NAO"
            p["motivo"] = "Agencia nao respondeu a tempo."
            self.registro.registrar("2PC_VOTO_TIMEOUT", self.relogio.evento_local(), {"txId": tx_id, "agencia": p["agencia"]})

    def _entregar_decisao(self, tx_id: str, coord: dict, p: dict) -> None:
        if p["confirmou"]:
            return
        try:
            vetor_envio = self.relogio.ao_enviar()
            self.registro.registrar(
                "2PC_DECISAO_ENVIADA", vetor_envio, {"txId": tx_id, "para": p["agencia"], "decisao": coord["decisao"]}
            )
            resp = self.cliente.post(
                f"{config.url_da_agencia(p['agencia'])}/2pc/decidir",
                {"txId": tx_id, "decisao": coord["decisao"], "vetorEnvio": vetor_envio},
                timeout=config.TIMEOUT_2PC,
            )
            if resp.get("vetorEnvio"):
                self.relogio.ao_receber(resp["vetorEnvio"])
            p["confirmou"] = True
        except Exception:
            pass  # participante fora do ar: a reentrega periodica tenta de novo

    def _concluir_se_tudo_confirmado(self, coord: dict) -> None:
        with self.estado.lock:
            if coord["estado"] == "DECIDIDA" and all(p["confirmou"] for p in coord["participantes"]):
                coord["estado"] = "CONCLUIDA"
                self.estado.salvar()
                self.registro.registrar(
                    "2PC_CONCLUIDA", self.relogio.evento_local(), {"txId": coord["txId"], "decisao": coord["decisao"]}
                )

    @staticmethod
    def _resumo(coord: dict) -> dict:
        return {
            "txId": coord["txId"],
            "resultado": coord["decisao"],
            "motivos": [p["motivo"] for p in coord["participantes"] if p["voto"] != "SIM"],
            "pendentesDeConfirmacao": [p["agencia"] for p in coord["participantes"] if not p["confirmou"]],
        }

    @staticmethod
    def _em_paralelo(funcao, itens) -> None:
        with ThreadPoolExecutor(max_workers=len(itens)) as pool:
            list(pool.map(funcao, itens))

    def coordenar(self, id_origem: int, id_destino: int, valor: float) -> dict:
        tx_id = str(uuid.uuid4())

        def participante(id_conta: int, tipo: str) -> dict:
            return {
                "agencia": config.agencia_responsavel(id_conta),
                "operacao": {"tipo": tipo, "idConta": id_conta, "valor": valor},
                "voto": None,
                "motivo": None,
                "confirmou": False,
            }

        coord = {
            "txId": tx_id,
            "estado": "PREPARANDO",
            "decisao": None,
            "participantes": [participante(id_origem, "DEBITO"), participante(id_destino, "CREDITO")],
        }
        with self.estado.lock:
            self.estado.coordenacoes[tx_id] = coord
            self.estado.salvar()
        self.registro.registrar(
            "2PC_INICIO", self.relogio.evento_local(), {"txId": tx_id, "idOrigem": id_origem, "idDestino": id_destino, "valor": valor}
        )

        # FASE 1: pergunta a todos se podem se comprometer
        self._em_paralelo(lambda p: self._pedir_voto(tx_id, p), coord["participantes"])
        falhar("coordenador-antes-de-decidir")

        # DECISAO: commit so se TODOS votaram SIM. Gravar em disco e o ponto sem volta.
        with self.estado.lock:
            coord["decisao"] = "COMMIT" if all(p["voto"] == "SIM" for p in coord["participantes"]) else "ABORT"
            coord["estado"] = "DECIDIDA"
            self.estado.salvar()
        self.registro.registrar(f"2PC_DECISAO_{coord['decisao']}", self.relogio.evento_local(), {"txId": tx_id})
        falhar("coordenador-apos-decidir")
        if self.eventos_nuvem:
            self.eventos_nuvem.publicar_decisao(coord)  # opcional, fora do caminho critico

        # FASE 2: comunica a decisao a todos
        self._em_paralelo(lambda p: self._entregar_decisao(tx_id, coord, p), coord["participantes"])
        self._concluir_se_tudo_confirmado(coord)
        return self._resumo(coord)

    def reentregar_pendentes(self) -> None:
        if not self._reentregando.acquire(blocking=False):
            return
        try:
            with self.estado.lock:
                decididas = [c for c in self.estado.coordenacoes.values() if c["estado"] == "DECIDIDA"]
            for coord in decididas:
                pendentes = [p for p in coord["participantes"] if not p["confirmou"]]
                if pendentes:
                    self._em_paralelo(lambda p: self._entregar_decisao(coord["txId"], coord, p), pendentes)
                self._concluir_se_tudo_confirmado(coord)
        finally:
            self._reentregando.release()

    def recuperar(self) -> None:
        """Chamado UMA vez ao subir, antes de aceitar requisicoes. Transacao que
        estava na fase 1 nunca chegou a uma decisao: e abortada. E seguro porque
        ninguem pode ter recebido COMMIT (ele nunca foi decidido)."""
        mudou = False
        for coord in self.estado.coordenacoes.values():
            if coord["estado"] == "PREPARANDO":
                coord["decisao"] = "ABORT"
                coord["estado"] = "DECIDIDA"
                mudou = True
                self.registro.registrar("2PC_ABORTO_PRESUMIDO", self.relogio.evento_local(), {"txId": coord["txId"]})
        if mudou:
            self.estado.salvar()

    def status_de(self, tx_id: str) -> dict:
        """Resposta ao participante em duvida: qual foi a decisao?"""
        coord = self.estado.coordenacoes.get(tx_id)
        if not coord:
            return {"decisao": "ABORT", "observacao": "transacao desconhecida (aborto presumido)"}
        return {"decisao": coord["decisao"] or "EM_ANDAMENTO"}

    def iniciar_reentrega(self) -> None:
        def _laco() -> None:
            while True:
                threading.Event().wait(config.INTERVALO_REENTREGA)
                self.reentregar_pendentes()

        threading.Thread(target=_laco, daemon=True, name=f"reentrega-agencia-{self.id_agencia}").start()
