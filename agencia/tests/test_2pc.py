"""Protocolo 2PC: participante, coordenador, recuperacao e persistencia."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src import config
from src.app import criar_app
from src.services import auth_service, falhas
from tests.rede_2pc import montar_agencias

TOKEN = {"x-token-interno": "token-de-teste"}


@pytest.fixture
def ag():
    apps, rede = montar_agencias()
    for i, nome in ((0, "Ana"), (1, "Bia")):
        apps[i].state.contas[i] = {"id": i, "nomeAluno": nome, "saldo": 100.0, "versao": [0, 0, 0]}
    return apps, rede


def _soma(apps):
    return sum(c["saldo"] for a in apps.values() for c in a.state.contas.values())


def _reservas(apps):
    return sum(c.get("reservado", 0) for a in apps.values() for c in a.state.contas.values())


def test_preparar_reserva_e_decidir_commit_e_idempotente(ag):
    apps, _ = ag
    p = apps[0].state.participante
    op = {"tipo": "DEBITO", "idConta": 0, "valor": 30.0}
    assert p.preparar("t1", op, 2)["voto"] == "SIM"
    assert p.preparar("t1", op, 2)["voto"] == "SIM"  # pergunta repetida: nao reserva de novo
    conta = apps[0].state.contas[0]
    assert (conta["saldo"], conta["reservado"]) == (100, 30)
    p.decidir("t1", "COMMIT")
    p.decidir("t1", "COMMIT")  # decisao repetida: nao debita de novo
    assert (conta["saldo"], conta["reservado"]) == (70, 0)


def test_abort_libera_reserva(ag):
    apps, _ = ag
    p = apps[0].state.participante
    p.preparar("t1", {"tipo": "DEBITO", "idConta": 0, "valor": 30.0}, 2)
    p.decidir("t1", "ABORT")
    assert (apps[0].state.contas[0]["saldo"], apps[0].state.contas[0]["reservado"]) == (100, 0)


def test_voto_nao_nao_reserva_e_lembra_do_aborto(ag):
    apps, _ = ag
    p = apps[0].state.participante
    op = {"tipo": "DEBITO", "idConta": 0, "valor": 500.0}
    assert p.preparar("t1", op, 2)["voto"] == "NAO"
    assert p.preparar("t1", op, 2)["voto"] == "NAO"
    assert apps[0].state.contas[0].get("reservado", 0) == 0


def test_decidir_abort_de_transacao_desconhecida_e_ok_mas_commit_e_erro(ag):
    p = ag[0][0].state.participante
    assert p.decidir("ninguem", "ABORT")["ok"] is True
    assert "erro" in p.decidir("ninguem", "COMMIT")


def test_reserva_bloqueia_saque_do_dinheiro_em_duvida(ag):
    apps, _ = ag
    c = TestClient(apps[0], headers={"Authorization": f"Bearer {auth_service.criar_token('aluno')}"})
    apps[0].state.participante.preparar("t1", {"tipo": "DEBITO", "idConta": 0, "valor": 80.0}, 2)
    corpo = c.get("/contas/0").json()
    assert (corpo["saldo"], corpo["reservado"], corpo["disponivel"]) == (100, 80, 20)
    assert c.post("/contas/0/sacar", json={"valor": 50}).status_code == 400
    assert c.post("/contas/0/sacar", json={"valor": 20}).status_code == 200


def test_duas_transferencias_simultaneas_nao_gastam_o_mesmo_dinheiro(ag):
    apps, _ = ag
    p = apps[0].state.participante
    assert p.preparar("a", {"tipo": "DEBITO", "idConta": 0, "valor": 60.0}, 2)["voto"] == "SIM"
    assert p.preparar("b", {"tipo": "DEBITO", "idConta": 0, "valor": 60.0}, 2)["voto"] == "NAO"


def test_participante_fora_do_ar_na_fase_1_aborta_e_libera_reserva(ag):
    apps, rede = ag
    rede.fora.add(1)
    r = apps[2].state.coordenador.coordenar(0, 1, 10.0)
    assert r["resultado"] == "ABORT"
    assert "nao respondeu" in r["motivos"][0]
    assert _reservas(apps) == 0 and _soma(apps) == 200


def test_decisao_commit_nao_entregue_e_reentregue_depois(ag):
    apps, rede = ag
    rede.sem_decisao.add(1)
    coord = apps[2].state.coordenador
    r = coord.coordenar(0, 1, 10.0)
    assert r["resultado"] == "COMMIT" and r["pendentesDeConfirmacao"] == [1]
    assert apps[0].state.contas[0]["saldo"] == 90 and apps[1].state.contas[1]["saldo"] == 100  # meio-aplicado, por enquanto
    rede.sem_decisao.clear()
    coord.reentregar_pendentes()
    assert apps[1].state.contas[1]["saldo"] == 110
    assert apps[2].state.estado.coordenacoes[r["txId"]]["estado"] == "CONCLUIDA"
    assert _soma(apps) == 200


def test_participante_em_duvida_pergunta_ao_coordenador_que_desconhece_e_recebe_abort(ag):
    """Cenario 3 (coordenador caiu antes de decidir e voltou sem registro): aborto presumido."""
    apps, _ = ag
    apps[0].state.participante.preparar("t1", {"tipo": "DEBITO", "idConta": 0, "valor": 30.0}, 2)
    apps[0].state.participante.resolver_em_duvida()
    assert apps[0].state.contas[0]["reservado"] == 0
    assert apps[0].state.estado.participacoes["t1:DEBITO"]["estado"] == "ABORTADO"


def test_participante_em_duvida_bloqueia_enquanto_coordenador_esta_fora(ag):
    apps, rede = ag
    p = apps[0].state.participante
    p.preparar("t1", {"tipo": "DEBITO", "idConta": 0, "valor": 30.0}, 2)
    rede.fora.add(2)
    p.resolver_em_duvida()
    assert apps[0].state.contas[0]["reservado"] == 30  # preso: nao decide sozinho
    eventos = [e["tipo"] for e in apps[0].state.registro.ler()]
    assert "2PC_BLOQUEADA_AGUARDANDO_COORDENADOR" in eventos
    rede.fora.clear()
    p.resolver_em_duvida()
    assert apps[0].state.contas[0]["reservado"] == 0


def test_participante_em_duvida_aplica_commit_decidido(ag):
    apps, rede = ag
    rede.sem_decisao.update({0, 1})
    r = apps[2].state.coordenador.coordenar(0, 1, 10.0)
    assert r["resultado"] == "COMMIT"
    rede.sem_decisao.clear()
    apps[0].state.participante.resolver_em_duvida()
    assert apps[0].state.contas[0]["saldo"] == 90


def test_recuperar_aborta_transacao_que_estava_na_fase_1(ag):
    apps, _ = ag
    estado = apps[2].state.estado
    estado.coordenacoes["tx"] = {"txId": "tx", "estado": "PREPARANDO", "decisao": None, "participantes": []}
    assert apps[2].state.coordenador.status_de("tx") == {"decisao": "EM_ANDAMENTO"}
    apps[2].state.coordenador.recuperar()
    assert estado.coordenacoes["tx"]["decisao"] == "ABORT"
    assert apps[2].state.coordenador.status_de("tx")["decisao"] == "ABORT"
    assert "2PC_ABORTO_PRESUMIDO" in [e["tipo"] for e in apps[2].state.registro.ler()]


def test_recuperar_preserva_decisao_commit_ja_gravada(ag):
    apps, _ = ag
    estado = apps[2].state.estado
    estado.coordenacoes["tx"] = {"txId": "tx", "estado": "DECIDIDA", "decisao": "COMMIT", "participantes": []}
    apps[2].state.coordenador.recuperar()
    assert apps[2].state.coordenador.status_de("tx")["decisao"] == "COMMIT"


# ---- persistencia ----


def test_estado_sobrevive_a_reinicio_incluindo_reserva_e_promessa(ag):
    apps, _ = ag
    apps[0].state.participante.preparar("t1", {"tipo": "DEBITO", "idConta": 0, "valor": 30.0}, 2)
    reiniciada = criar_app(id_agencia=0, iniciar_consumidor=False, iniciar_bully=False)
    assert reiniciada.state.contas[0]["reservado"] == 30
    assert reiniciada.state.estado.participacoes["t1:DEBITO"]["estado"] == "PREPARADO"
    reiniciada.state.participante.decidir("t1", "COMMIT")  # e a promessa ainda pode ser cumprida
    assert reiniciada.state.contas[0]["saldo"] == 70


def test_gravacao_atomica_nao_deixa_temporario_e_arquivo_e_json_valido(ag):
    apps, _ = ag
    estado = apps[0].state.estado
    estado.salvar()
    assert json.loads(estado.caminho.read_text(encoding="utf-8"))["contas"]["0"]["saldo"] == 100
    assert not estado.caminho.with_name(estado.caminho.name + ".tmp").exists()


# ---- rotas internas e falhas ----


def test_rotas_2pc_exigem_token(ag):
    apps, _ = ag
    c = TestClient(apps[0])
    for metodo, rota in (("get", "/2pc/transacoes"), ("get", "/2pc/status/x"), ("post", "/2pc/preparar"), ("post", "/2pc/decidir")):
        assert getattr(c, metodo)(rota).status_code == 401
        assert getattr(c, metodo)(rota, headers={"x-token-interno": "errado"}).status_code == 401
    assert c.get("/2pc/transacoes", headers=TOKEN).status_code == 200


def test_sem_token_configurado_rotas_internas_falham_fechadas(ag, monkeypatch):
    monkeypatch.setattr(config, "TOKEN_INTERNO", "")
    assert TestClient(ag[0][0]).get("/2pc/transacoes", headers={"x-token-interno": ""}).status_code == 401


def test_decidir_transacao_desconhecida_commit_responde_409(ag):
    r = TestClient(ag[0][0]).post("/2pc/decidir", json={"txId": "x", "decisao": "COMMIT"}, headers=TOKEN)
    assert r.status_code == 409


def test_falha_injetada_derruba_uma_unica_vez(tmp_path, monkeypatch):
    saidas = []
    monkeypatch.setattr(os, "_exit", saidas.append)
    monkeypatch.setenv("FALHA_2PC", "coordenador-apos-decidir")
    monkeypatch.setenv("AGENCIA_ID", "2")
    (tmp_path / "dados").mkdir()
    falhas.falhar("outro-ponto")
    assert saidas == []
    falhas.falhar("coordenador-apos-decidir")
    falhas.falhar("coordenador-apos-decidir")  # marcador: nao cai de novo no reinicio
    assert saidas == [1]


def test_saude_e_publica(ag):
    assert TestClient(ag[0][0]).get("/saude").json() == {"status": "ok"}
