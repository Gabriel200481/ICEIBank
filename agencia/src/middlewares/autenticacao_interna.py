import hmac

from fastapi import Header, HTTPException

from src import config


def autenticacao_interna(x_token_interno: str | None = Header(default=None)) -> None:
    """Protege as rotas que so outras agencias deveriam chamar (Bully e 2PC)."""
    if not config.TOKEN_INTERNO or not x_token_interno or not hmac.compare_digest(x_token_interno, config.TOKEN_INTERNO):
        raise HTTPException(status_code=401, detail="Token interno ausente ou invalido.")
