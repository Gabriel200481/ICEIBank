"""Rede falsa para testar o 2PC sem sockets: leva as chamadas internas de uma
agencia para as rotas REAIS (via TestClient) das outras, com o token interno."""

from fastapi.testclient import TestClient

from src import config
from src.app import criar_app


class Rede:
    def __init__(self, apps: dict):
        self.clientes = {i: TestClient(a) for i, a in apps.items()}
        self.fora: set[int] = set()  # agencias "derrubadas": a chamada falha
        self.sem_decisao: set[int] = set()  # agencias que nao recebem /2pc/decidir

    def _alvo(self, url: str, caminho_proibido: str | None = None):
        for i, c in self.clientes.items():
            base = config.url_da_agencia(i)
            if url.startswith(base + "/"):
                if i in self.fora or (url.endswith("/2pc/decidir") and i in self.sem_decisao):
                    raise ConnectionError(f"agencia {i} fora do ar")
                return c, url[len(base):]
        raise AssertionError(url)

    def post(self, url, corpo, timeout):
        c, caminho = self._alvo(url)
        r = c.post(caminho, json=corpo, headers={"x-token-interno": config.TOKEN_INTERNO})
        r.raise_for_status()
        return r.json()

    def encaminhar(self, url, corpo, timeout):
        c, caminho = self._alvo(url)
        r = c.post(caminho, json=corpo, headers={"x-token-interno": config.TOKEN_INTERNO})
        return r.status_code, r.json()

    def get(self, url, timeout):
        c, caminho = self._alvo(url)
        r = c.get(caminho, headers={"x-token-interno": config.TOKEN_INTERNO})
        r.raise_for_status()
        return r.json()


def montar_agencias(tmp_path_unused=None):
    apps = {i: criar_app(id_agencia=i, iniciar_consumidor=False, iniciar_bully=False) for i in range(3)}
    rede = Rede(apps)
    for a in apps.values():
        a.state.coordenador.cliente = rede
        a.state.participante.cliente = rede
    for a in apps.values():
        a.state.bully._lider_atual = 2  # a maior agencia e a lider
    return apps, rede
