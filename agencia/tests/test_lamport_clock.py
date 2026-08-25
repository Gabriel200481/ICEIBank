from src.services.lamport_clock import RelogioLamport


def test_evento_local_incrementa_contador():
    relogio = RelogioLamport()
    assert relogio.evento_local() == 1
    assert relogio.evento_local() == 2


def test_ao_enviar_incrementa_contador():
    relogio = RelogioLamport()
    relogio.evento_local()  # contador = 1
    assert relogio.ao_enviar() == 2


def test_ao_receber_usa_max_mais_um_quando_recebido_e_maior():
    relogio = RelogioLamport()
    relogio.contador = 5
    novo = relogio.ao_receber(10)
    assert novo == 11


def test_ao_receber_usa_max_mais_um_quando_local_e_maior():
    relogio = RelogioLamport()
    relogio.contador = 10
    novo = relogio.ao_receber(3)
    assert novo == 11


def test_relogios_diferentes_sao_independentes():
    relogio_a = RelogioLamport()
    relogio_b = RelogioLamport()
    relogio_a.evento_local()
    relogio_a.evento_local()
    assert relogio_a.contador == 2
    assert relogio_b.contador == 0
