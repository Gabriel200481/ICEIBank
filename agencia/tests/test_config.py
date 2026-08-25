from src import config


def test_particionamento_conta_0_agencia_0():
    assert config.agencia_responsavel(0) == 0


def test_particionamento_conta_1_agencia_1():
    assert config.agencia_responsavel(1) == 1


def test_particionamento_conta_3_volta_para_agencia_0():
    assert config.agencia_responsavel(3) == 0


def test_numero_de_agencias_e_tres():
    assert config.NUMERO_AGENCIAS == 3
    assert len(config.AGENCIAS) == 3


def test_url_da_agencia_bate_com_porta_base():
    assert config.url_da_agencia(0) == f"http://localhost:{config.PORTA_BASE}"
    assert config.url_da_agencia(2) == f"http://localhost:{config.PORTA_BASE + 2}"
