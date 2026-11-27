import os
import tempfile

import pytest

# Define antes de qualquer import de src.config: evita que o app criado em
# nivel de modulo (src.app.app) dispare eleicoes reais durante os testes, e
# mantem o estado/logs dele fora de agencia/data.
os.environ.setdefault("BULLY_DESLIGADO", "1")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="iceibank-testes-"))
os.environ.setdefault("TOKEN_INTERNO", "token-de-teste")

from src import config  # noqa: E402


@pytest.fixture(autouse=True)
def estado_isolado(tmp_path, monkeypatch):
    """Cada teste comeca com disco limpo: o estado das agencias agora e duravel."""
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path / "dados"))
    monkeypatch.setattr(config, "TOKEN_INTERNO", "token-de-teste")
