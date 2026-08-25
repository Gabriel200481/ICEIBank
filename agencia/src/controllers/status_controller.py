"""Funcionalidade adicional (secao 2.1 do roteiro): rota de status/health-check
por agencia, sem autenticacao (health-checks precisam ser alcancaveis sem uma
sessao de usuario - ver justificativa em RESPOSTAS.md).
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/status")
def status(request: Request):
    estado = request.app.state
    return {
        "idAgencia": estado.id_agencia,
        "timestampLamportAtual": estado.relogio.contador,
        "quantidadeContas": len(estado.contas),
    }
