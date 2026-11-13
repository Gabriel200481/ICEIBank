"""Eleicao de lider pelo algoritmo de Bully (Sprint 3).

Regra: entre as agencias vivas, o maior ID vence. Uma agencia que inicia
uma eleicao envia "eleicao" so para os IDs MAIORES que o seu:
- se nenhum responder, ela e a maior viva: vira lider e avisa todas
  ("coordenador");
- se algum responder, esse (maior) assume a eleicao, e a agencia aguarda o
  "coordenador" dele (se ele nao anunciar a tempo, ela tenta de novo).

O estado compartilhado (lider_atual) e acessado pela thread de heartbeat e
pelas threads do servidor HTTP, entao fica protegido por um Lock - do mesmo
jeito que o relogio vetorial precisou de cuidado com concorrencia.
"""

import threading
from typing import Callable

import httpx

from src.services.event_log import RegistroEventos
from src.services.vector_clock import RelogioVetorial

TIMEOUT_HTTP = 1.0

# enviar(id_destino, caminho, corpo) -> True se a agencia respondeu 200 com
# {"resposta": "OK"} (eleicao) ou 200 (coordenador); False se caiu/timeout.
Enviar = Callable[[int, str, dict], bool]


def enviar_http(agencias: list[dict], timeout: float = TIMEOUT_HTTP) -> Enviar:
    urls = {a["id"]: a["url"] for a in agencias}

    def enviar(id_destino: int, caminho: str, corpo: dict) -> bool:
        try:
            resposta = httpx.post(urls[id_destino] + caminho, json=corpo, timeout=timeout)
        except httpx.HTTPError:
            # Cobre timeout e conexao recusada: para o Bully, "nao respondeu"
            # significa "considerada fora do ar".
            return False
        if resposta.status_code != 200:
            return False
        if caminho == "/bully/eleicao":
            return resposta.json().get("resposta") == "OK"
        return True

    return enviar


def _em_thread(funcao: Callable[[], None]) -> None:
    threading.Thread(target=funcao, daemon=True).start()


class Bully:
    def __init__(
        self,
        id_agencia: int,
        ids_agencias: list[int],
        relogio: RelogioVetorial,
        registro: RegistroEventos,
        enviar: Enviar,
        espera_coordenador: float = 3.0,
        agendar: Callable[[Callable[[], None]], None] = _em_thread,
    ) -> None:
        self.id_agencia = id_agencia
        self.ids_agencias = ids_agencias
        self.relogio = relogio
        self.registro = registro
        self._enviar = enviar
        self._espera_coordenador = espera_coordenador
        self._agendar = agendar

        self._lock = threading.Lock()
        self._lider_atual: int | None = None
        self._em_eleicao = False
        self._coordenador_recebido = threading.Event()

    @property
    def lider_atual(self) -> int | None:
        with self._lock:
            return self._lider_atual

    def _definir_lider(self, id_lider: int) -> bool:
        """Retorna True se o lider mudou."""
        with self._lock:
            mudou = self._lider_atual != id_lider
            self._lider_atual = id_lider
        return mudou

    def iniciar_eleicao(self) -> None:
        # Uma eleicao por vez em cada agencia: a "tempestade" inicial faz as
        # outras agencias dispararem varias eleicoes seguidas na mesma.
        with self._lock:
            if self._em_eleicao:
                return
            self._em_eleicao = True
            self._coordenador_recebido.clear()
        try:
            self._executar_eleicao()
        finally:
            with self._lock:
                self._em_eleicao = False

    def _executar_eleicao(self) -> None:
        ts = self.relogio.evento_local()
        self.registro.registrar("ELEICAO_INICIADA", ts, {"agencia": self.id_agencia})

        maiores = [i for i in self.ids_agencias if i > self.id_agencia]
        algum_respondeu = False
        for id_maior in maiores:
            corpo = {"origemId": self.id_agencia, "vetor": self.relogio.ao_enviar()}
            if self._enviar(id_maior, "/bully/eleicao", corpo):
                algum_respondeu = True

        if not algum_respondeu:
            self._assumir_lideranca()
            return

        # Uma agencia maior esta viva e vai conduzir a eleicao: aguarda o
        # anuncio. Se ele nao vier a tempo (a maior caiu no meio), recomeca.
        if not self._coordenador_recebido.wait(self._espera_coordenador):
            with self._lock:
                self._em_eleicao = False
            self.iniciar_eleicao()

    def _assumir_lideranca(self) -> None:
        mudou = self._definir_lider(self.id_agencia)
        for id_outro in self.ids_agencias:
            if id_outro == self.id_agencia:
                continue
            corpo = {"liderId": self.id_agencia, "vetor": self.relogio.ao_enviar()}
            self._enviar(id_outro, "/bully/coordenador", corpo)
        ts = self.relogio.evento_local()
        if mudou:
            self.registro.registrar("NOVO_LIDER", ts, {"liderId": self.id_agencia, "agencia": self.id_agencia})

    def receber_eleicao(self, origem_id: int, vetor: list[int]) -> dict:
        self.relogio.ao_receber(vetor)
        if self.id_agencia > origem_id:
            # Sou maior: respondo "OK" (estou vivo) e assumo a eleicao.
            self._agendar(self.iniciar_eleicao)
            return {"resposta": "OK", "idAgencia": self.id_agencia}
        return {"resposta": "IGNORADO", "idAgencia": self.id_agencia}

    def receber_coordenador(self, lider_id: int, vetor: list[int]) -> None:
        ts = self.relogio.ao_receber(vetor)
        if self._definir_lider(lider_id):
            self.registro.registrar("NOVO_LIDER", ts, {"liderId": lider_id, "agencia": self.id_agencia})
        self._coordenador_recebido.set()
