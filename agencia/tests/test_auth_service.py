from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.services import auth_service


def test_criar_e_decodificar_token_valido():
    token = auth_service.criar_token("aluno")
    payload = auth_service.decodificar_token(token)
    assert payload["sub"] == "aluno"


def test_token_expirado_levanta_excecao():
    agora = datetime.now(timezone.utc)
    payload = {"sub": "aluno", "iat": agora - timedelta(minutes=20), "exp": agora - timedelta(minutes=5)}
    token_expirado = jwt.encode(payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)

    with pytest.raises(jwt.ExpiredSignatureError):
        auth_service.decodificar_token(token_expirado)


def test_token_com_assinatura_invalida_levanta_excecao():
    token_com_outra_chave = jwt.encode({"sub": "aluno"}, "outra-chave", algorithm=auth_service.ALGORITHM)

    with pytest.raises(jwt.InvalidTokenError):
        auth_service.decodificar_token(token_com_outra_chave)
