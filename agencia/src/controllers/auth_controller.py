import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.services import auth_service

router = APIRouter()

# Credenciais de demonstracao para este sprint: o escopo do Sprint 1 nao
# inclui cadastro/tabela de usuarios (isso nao faz parte do roteiro), entao
# a validacao de login usa uma unica credencial fixa por processo. A decisao
# de design (por que esse formato) esta documentada em RESPOSTAS.md.
USUARIOS_DEMO = {"aluno": "senha123"}


class LoginBody(BaseModel):
    usuario: str
    senha: str


@router.post("/auth/login")
def login(body: LoginBody):
    senha_esperada = USUARIOS_DEMO.get(body.usuario)
    if senha_esperada is None or senha_esperada != body.senha:
        raise HTTPException(status_code=401, detail="Usuario ou senha invalidos.")
    token = auth_service.criar_token(body.usuario)
    return {"access_token": token, "token_type": "bearer"}


def exigir_usuario_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Dependency do FastAPI: protege rotas que exigem um usuario logado
    (frontend). Levanta 401 se o token estiver ausente, invalido ou expirado.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = auth_service.decodificar_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido.")

    return payload["sub"]


def exigir_token_de_servico(authorization: str | None = Header(default=None)) -> None:
    """Dependency do FastAPI: protege a chamada agencia-a-agencia
    (creditar-remoto) com um segredo compartilhado entre as agencias, em vez
    do JWT de usuario do frontend - justificativa em RESPOSTAS.md (secao 11).
    """
    if not authorization or not authorization.startswith("Service "):
        raise HTTPException(status_code=401, detail="Token de servico ausente.")

    token = authorization.removeprefix("Service ").strip()
    if token != auth_service.SERVICE_TOKEN:
        raise HTTPException(status_code=401, detail="Token de servico invalido.")
