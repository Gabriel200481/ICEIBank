import pytest
from fastapi.testclient import TestClient

from src.app import criar_app
from src.services.bully import Bully
from src.services.event_log import RegistroEventos
from src.services.vector_clock import RelogioVetorial

IDS = [0, 1, 2]


class RedeFalsa:
    """Simula a rede entre agencias: cada agencia registrada recebe as
    chamadas direto nos metodos receber_* (sem HTTP). Agencias em `fora`
    nao respondem (como se estivessem caidas)."""

    def __init__(self):
        self.agencias: dict[int, Bully] = {}
        self.fora: set[int] = set()
        self.chamadas: list[tuple[int, int, str]] = []

    def enviar_de(self, origem: int):
        def enviar(destino: int, caminho: str, corpo: dict) -> bool:
            self.chamadas.append((origem, destino, caminho))
            if destino in self.fora or destino not in self.agencias:
                return False
            alvo = self.agencias[destino]
            if caminho == "/bully/eleicao":
                resposta = alvo.receber_eleicao(corpo["origemId"], corpo["vetor"])
                return resposta["resposta"] == "OK"
            alvo.receber_coordenador(corpo["liderId"], corpo["vetor"])
            return True

        return enviar


def montar(tmp_path, rede: RedeFalsa, id_agencia: int, agendar=None) -> Bully:
    registro = RegistroEventos(f"agencia-{id_agencia}", pasta_dados=str(tmp_path))
    bully = Bully(
        id_agencia,
        IDS,
        RelogioVetorial(id_agencia, len(IDS)),
        registro,
        rede.enviar_de(id_agencia),
        espera_coordenador=0.2,
        agendar=agendar or (lambda f: f()),
    )
    rede.agencias[id_agencia] = bully
    return bully


@pytest.fixture
def rede():
    return RedeFalsa()


def test_agencia_de_maior_id_vira_lider_quando_ninguem_responde(tmp_path, rede):
    bully = montar(tmp_path, rede, 2)
    bully.iniciar_eleicao()
    assert bully.lider_atual == 2


def test_agencia_de_menor_id_nao_envia_eleicao_para_ids_menores(tmp_path, rede):
    bully = montar(tmp_path, rede, 2)
    bully.iniciar_eleicao()
    eleicoes = [c for c in rede.chamadas if c[2] == "/bully/eleicao"]
    assert eleicoes == []  # nenhum ID maior que 2 existe


def test_as_tres_agencias_convergem_para_a_maior(tmp_path, rede):
    a0, a1, a2 = (montar(tmp_path, rede, i) for i in IDS)
    # "Tempestade": todas iniciam eleicao ao subir, na ordem 0, 1, 2.
    a0.iniciar_eleicao()
    a1.iniciar_eleicao()
    a2.iniciar_eleicao()
    assert {a0.lider_atual, a1.lider_atual, a2.lider_atual} == {2}


def test_convergencia_independe_da_ordem_de_subida(tmp_path, rede):
    a0, a1, a2 = (montar(tmp_path, rede, i) for i in IDS)
    a2.iniciar_eleicao()
    a0.iniciar_eleicao()
    a1.iniciar_eleicao()
    assert {a0.lider_atual, a1.lider_atual, a2.lider_atual} == {2}


def test_lider_2_fora_do_ar_elege_a_agencia_1(tmp_path, rede):
    a0, a1, _ = (montar(tmp_path, rede, i) for i in IDS)
    rede.fora.add(2)
    a0.iniciar_eleicao()
    assert a0.lider_atual == 1
    assert a1.lider_atual == 1


def test_so_a_agencia_0_viva_se_elege(tmp_path, rede):
    a0, _, _ = (montar(tmp_path, rede, i) for i in IDS)
    rede.fora.update({1, 2})
    a0.iniciar_eleicao()
    assert a0.lider_atual == 0


def test_eleicao_de_id_maior_nao_e_respondida_por_id_menor(tmp_path, rede):
    a1 = montar(tmp_path, rede, 1)
    resposta = a1.receber_eleicao(origem_id=2, vetor=[0, 0, 1])
    assert resposta["resposta"] == "IGNORADO"


def test_eleicao_de_id_menor_e_respondida_com_ok_e_dispara_eleicao(tmp_path, rede):
    disparos = []
    a2 = montar(tmp_path, rede, 2, agendar=disparos.append)
    resposta = a2.receber_eleicao(origem_id=0, vetor=[1, 0, 0])
    assert resposta["resposta"] == "OK"
    assert len(disparos) == 1  # a eleicao propria foi agendada, nao bloqueou


def test_coordenador_atualiza_lider_e_vetor(tmp_path, rede):
    a0 = montar(tmp_path, rede, 0)
    a0.receber_coordenador(2, [0, 0, 4])
    assert a0.lider_atual == 2
    assert a0.relogio.vetor[2] == 4


def test_eleicoes_simultaneas_na_mesma_agencia_executam_uma_vez(tmp_path, rede):
    a2 = montar(tmp_path, rede, 2)
    a2._em_eleicao = True  # ja ha uma eleicao em curso
    a2.iniciar_eleicao()
    assert a2.lider_atual is None


def test_se_a_maior_responde_mas_nao_anuncia_a_eleicao_recomeca(tmp_path, rede):
    a0 = montar(tmp_path, rede, 0)
    # A agencia 2 "responde OK" na eleicao mas nunca anuncia (cai logo depois).
    chamadas = {"n": 0}

    def enviar(destino, caminho, corpo):
        if caminho == "/bully/eleicao" and destino == 2:
            chamadas["n"] += 1
            if chamadas["n"] == 1:
                return True  # 1a vez: respondeu OK e sumiu
            return False  # 2a vez: caiu de vez
        return False

    a0._enviar = enviar
    a0.iniciar_eleicao()
    # 2 nao responde mais, 1 tambem nao: a 0 acaba assumindo.
    assert a0.lider_atual == 0
    assert chamadas["n"] == 2


def test_eventos_de_eleicao_e_novo_lider_sao_registrados(tmp_path, rede):
    a2 = montar(tmp_path, rede, 2)
    a2.iniciar_eleicao()
    linhas = (tmp_path / "eventos-agencia-2.jsonl").read_text(encoding="utf-8")
    assert "ELEICAO_INICIADA" in linhas
    assert "NOVO_LIDER" in linhas


# ---- Rotas HTTP ----

@pytest.fixture
def cliente(tmp_path):
    app = criar_app(id_agencia=1, iniciar_consumidor=False, iniciar_bully=False)
    app.state.registro.caminho_arquivo = tmp_path / "eventos.jsonl"
    app.state.bully._agendar = lambda f: None  # nao dispara eleicao de verdade
    return TestClient(app)


def test_get_lider_sem_lider_definido(cliente):
    resposta = cliente.get("/bully/lider")
    assert resposta.status_code == 200
    assert resposta.json() == {"liderId": None, "idAgencia": 1}


def test_post_coordenador_e_get_lider(cliente):
    resposta = cliente.post("/bully/coordenador", json={"liderId": 2, "vetor": [0, 0, 3]})
    assert resposta.status_code == 200
    assert cliente.get("/bully/lider").json()["liderId"] == 2


def test_post_eleicao_de_menor_id_recebe_ok(cliente):
    resposta = cliente.post("/bully/eleicao", json={"origemId": 0, "vetor": [1, 0, 0]})
    assert resposta.json()["resposta"] == "OK"


def test_post_eleicao_de_maior_id_e_ignorada(cliente):
    resposta = cliente.post("/bully/eleicao", json={"origemId": 2, "vetor": [0, 0, 1]})
    assert resposta.json()["resposta"] == "IGNORADO"


def test_rotas_bully_nao_exigem_jwt(cliente):
    assert "Authorization" not in cliente.headers
    assert cliente.get("/bully/lider").status_code == 200


def test_post_eleicao_com_corpo_invalido_retorna_422(cliente):
    assert cliente.post("/bully/eleicao", json={"origemId": "x"}).status_code == 422
