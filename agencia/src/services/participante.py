"""Papel de PARTICIPANTE no 2PC (Sprint 4, Parte B).

Cada agencia envolvida na transferencia (a do debito e a do credito) responde
a "preparar" (fase 1) e "decidir" (fase 2). Ao votar SIM ela se COMPROMETE: a
promessa vai para o disco ANTES da resposta. Tudo e idempotente.
"""

import threading

from src import config
from src.services import cliente_interno
from src.services.falhas import falhar
from src.services.saldo import saldo_disponivel


class Participante:
    def __init__(self, id_agencia, relogio, registro, estado, cliente=cliente_interno) -> None:
        self.id_agencia = id_agencia
        self.relogio = relogio
        self.registro = registro
        self.estado = estado
        self.cliente = cliente
        self._avisou_bloqueio: set[str] = set()
        self._resolvendo = threading.Lock()

    def preparar(self, tx_id: str, operacao: dict, coordenador: int, vetor_envio: list[int] | None = None) -> dict:
        with self.estado.lock:
            if vetor_envio:
                self.relogio.ao_receber(vetor_envio)

            # O tipo faz parte da chave: numa transferencia entre contas da MESMA
            # agencia, ela participa duas vezes da mesma transacao (debito e credito).
            chave = f"{tx_id}:{operacao['tipo']}"
            existente = self.estado.participacoes.get(chave)
            if existente:  # idempotencia: o coordenador pode repetir a pergunta
                voto = "NAO" if existente["estado"] == "ABORTADO" else "SIM"
                return {"voto": voto, "vetorEnvio": self.relogio.ao_enviar()}

            conta = self.estado.contas.get(operacao["idConta"])
            motivo = None
            if not conta:
                motivo = "Conta nao encontrada nesta agencia."
            elif operacao["tipo"] == "DEBITO" and saldo_disponivel(conta) < operacao["valor"]:
                motivo = "Saldo insuficiente."

            if motivo:
                self.estado.participacoes[chave] = {
                    "txId": tx_id, "coordenador": coordenador, "operacao": operacao, "estado": "ABORTADO", "motivo": motivo,
                }
                self.estado.salvar()
                self.registro.registrar("2PC_VOTO_NAO", self.relogio.evento_local(), {"txId": tx_id, "motivo": motivo})
                return {"voto": "NAO", "motivo": motivo, "vetorEnvio": self.relogio.ao_enviar()}

            if operacao["tipo"] == "DEBITO":
                conta["reservado"] = conta.get("reservado", 0) + operacao["valor"]  # o dinheiro fica "travado"
            self.estado.participacoes[chave] = {
                "txId": tx_id, "coordenador": coordenador, "operacao": operacao, "estado": "PREPARADO",
            }
            self.estado.salvar()  # promessa duravel ANTES de responder SIM
            self.registro.registrar("2PC_VOTO_SIM", self.relogio.evento_local(), {"txId": tx_id, "operacao": operacao})
            falhar("participante-apos-votar")  # caiu depois de se comprometer, antes de responder
            return {"voto": "SIM", "vetorEnvio": self.relogio.ao_enviar()}

    def decidir(self, tx_id: str, decisao: str, vetor_envio: list[int] | None = None) -> dict:
        """Aplica (COMMIT) ou descarta (ABORT) o que foi preparado. Idempotente."""
        with self.estado.lock:
            if vetor_envio:
                self.relogio.ao_receber(vetor_envio)

            minhas = [p for p in self.estado.participacoes.values() if p["txId"] == tx_id]
            if not minhas:
                if decisao == "ABORT":
                    return {"ok": True, "vetorEnvio": self.relogio.ao_enviar()}
                return {"erro": "Transacao desconhecida por este participante."}

            falhar("participante-antes-de-aplicar")  # caiu com a decisao em maos, sem aplica-la
            for p in minhas:
                if p["estado"] != "PREPARADO":
                    continue
                conta = self.estado.contas[p["operacao"]["idConta"]]
                tipo, valor = p["operacao"]["tipo"], p["operacao"]["valor"]
                ts = self.relogio.evento_local()
                if decisao == "COMMIT":
                    if tipo == "DEBITO":
                        conta["saldo"] -= valor
                        conta["reservado"] -= valor
                    else:
                        conta["saldo"] += valor
                    conta["versao"] = ts  # a versao da conta muda so quando o saldo muda (usada na sincronizacao)
                    p["estado"] = "COMMITADO"
                else:
                    if tipo == "DEBITO":
                        conta["reservado"] -= valor
                    p["estado"] = "ABORTADO"
                self.registro.registrar(
                    f"2PC_{decisao}_APLICADO", ts, {"txId": tx_id, "tipo": tipo, "valor": valor, "idConta": p["operacao"]["idConta"]},
                )
            self.estado.salvar()  # saldo, reserva e estado da transacao mudam juntos, de forma atomica
            return {"ok": True, "vetorEnvio": self.relogio.ao_enviar()}

    def resolver_em_duvida(self) -> None:
        """Votou SIM e a decisao nunca chegou: esta "em duvida" e NAO pode decidir
        sozinha. So resta perguntar ao coordenador, ate conseguir resposta."""
        if not self._resolvendo.acquire(blocking=False):
            return
        try:
            with self.estado.lock:
                pendentes = [dict(p) for p in self.estado.participacoes.values() if p["estado"] == "PREPARADO"]
            for p in pendentes:
                url = config.url_da_agencia(p["coordenador"])
                try:
                    decisao = self.cliente.get(f"{url}/2pc/status/{p['txId']}", timeout=config.TIMEOUT_2PC)["decisao"]
                except Exception:
                    if p["txId"] not in self._avisou_bloqueio:
                        self._avisou_bloqueio.add(p["txId"])
                        self.registro.registrar(
                            "2PC_BLOQUEADA_AGUARDANDO_COORDENADOR",
                            self.relogio.evento_local(),
                            {"txId": p["txId"], "coordenador": p["coordenador"]},
                        )
                    continue
                if decisao in ("COMMIT", "ABORT"):
                    self.registro.registrar(
                        "2PC_RESOLVIDA_POR_CONSULTA", self.relogio.evento_local(), {"txId": p["txId"], "decisao": decisao}
                    )
                    self.decidir(p["txId"], decisao)
                    self._avisou_bloqueio.discard(p["txId"])
        finally:
            self._resolvendo.release()

    def iniciar_resolucao(self) -> None:
        def _laco() -> None:
            while True:
                self.resolver_em_duvida()
                threading.Event().wait(config.INTERVALO_RESOLUCAO)

        threading.Thread(target=_laco, daemon=True, name=f"resolucao-agencia-{self.id_agencia}").start()
