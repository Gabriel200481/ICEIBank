"""Estado duravel da agencia (Sprint 4, Parte A).

Tudo que precisa sobreviver a uma queda (contas, operacoes de sincronizacao e
o estado das transacoes 2PC) vive em UM arquivo JSON, gravado de forma atomica:
escreve num temporario, forca a gravacao em disco (fsync) e so entao troca o
nome para o definitivo (os.replace e atomico). Assim saldo e estado da
transacao mudam juntos, ou nenhum dos dois muda.

Quem altera o estado segura `estado.lock` (RLock): o FastAPI atende cada
requisicao em uma thread e o 2PC tem threads proprias.

shortcut: reescreve o arquivo inteiro a cada mudanca, ok para o laboratorio;
um banco real usaria banco de dados com write-ahead log.
"""

import json
import os
import threading
from pathlib import Path

from src import config


class EstadoDuravel:
    def __init__(self, id_agencia: int, pasta: str | None = None) -> None:
        base = Path(pasta or config.DATA_DIR)
        base.mkdir(parents=True, exist_ok=True)
        self.caminho = base / f"estado-agencia-{id_agencia}.json"
        self.lock = threading.RLock()
        self.contas: dict[int, dict] = {}
        self.operacoes_aplicadas: dict[str, int] = {}
        self.coordenacoes: dict[str, dict] = {}  # txId -> transacao que esta agencia coordena
        self.participacoes: dict[str, dict] = {}  # "txId:TIPO" -> promessa/estado como participante
        self._carregar()

    def _carregar(self) -> None:
        if not self.caminho.exists():
            return
        dados = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.contas.update({int(k): v for k, v in dados["contas"].items()})
        self.operacoes_aplicadas.update(dados["operacoesAplicadas"])
        self.coordenacoes.update(dados["coordenacoes"])
        self.participacoes.update(dados["participacoes"])

    def salvar(self) -> None:
        with self.lock:
            dados = json.dumps(
                {
                    "contas": self.contas,
                    "operacoesAplicadas": self.operacoes_aplicadas,
                    "coordenacoes": self.coordenacoes,
                    "participacoes": self.participacoes,
                }
            )
            temporario = self.caminho.with_name(self.caminho.name + ".tmp")
            with open(temporario, "w", encoding="utf-8") as f:
                f.write(dados)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporario, self.caminho)
