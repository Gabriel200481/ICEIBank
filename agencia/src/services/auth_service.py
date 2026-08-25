"""Emissao e validacao de tokens JWT para autenticacao de usuario.

A chave secreta e o tempo de expiracao sao configuraveis por variavel de
ambiente para producao; os valores padrao aqui servem apenas para
desenvolvimento local (ver JWT_SECRET no .gitignore/README).
"""

import os
from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = os.environ.get("JWT_SECRET", "chave-secreta-de-desenvolvimento-iceibank-sprint1")
ALGORITHM = "HS256"
EXPIRACAO_MINUTOS = int(os.environ.get("JWT_EXPIRACAO_MINUTOS", "15"))

# Segredo compartilhado entre as 3 agencias para a chamada interna
# creditar-remoto (Parte D) - distinto do JWT de usuario. Justificativa em
# RESPOSTAS.md (secao 11).
SERVICE_TOKEN = os.environ.get("AGENCIA_SERVICE_TOKEN", "segredo-compartilhado-entre-agencias-iceibank")


def criar_token(usuario: str) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": usuario,
        "iat": agora,
        "exp": agora + timedelta(minutes=EXPIRACAO_MINUTOS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Levanta jwt.ExpiredSignatureError ou jwt.InvalidTokenError se o token
    for invalido/expirado - quem chama decide como converter em HTTP 401."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
