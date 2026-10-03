from src.services.vector_clock import RelogioVetorial


def test_evento_local_incrementa_a_propria_posicao():
    relogio = RelogioVetorial(id_agencia=0, numero_agencias=3)
    assert relogio.evento_local() == [1, 0, 0]
    assert relogio.evento_local() == [2, 0, 0]


def test_ao_enviar_incrementa_a_propria_posicao():
    relogio = RelogioVetorial(id_agencia=1, numero_agencias=3)
    relogio.evento_local()  # [0, 1, 0]
    assert relogio.ao_enviar() == [0, 2, 0]


def test_ao_receber_aplica_max_posicao_a_posicao_e_incrementa_a_propria():
    relogio = RelogioVetorial(id_agencia=1, numero_agencias=3)
    relogio.vetor = [2, 1, 0]
    novo = relogio.ao_receber([5, 0, 3])
    # max([2,1,0], [5,0,3]) = [5,1,3], depois incrementa a posicao 1
    assert novo == [5, 2, 3]


def test_cada_agencia_tem_vetor_independente():
    relogio_a = RelogioVetorial(id_agencia=0, numero_agencias=3)
    relogio_b = RelogioVetorial(id_agencia=1, numero_agencias=3)
    relogio_a.evento_local()
    relogio_a.evento_local()
    assert relogio_a.vetor == [2, 0, 0]
    assert relogio_b.vetor == [0, 0, 0]


def test_cenario_causal_completo_entre_duas_agencias():
    # Agencia 0 faz dois eventos locais, depois envia uma mensagem para a
    # Agencia 1, que ja tinha feito um evento local proprio.
    ag0 = RelogioVetorial(id_agencia=0, numero_agencias=2)
    ag1 = RelogioVetorial(id_agencia=1, numero_agencias=2)

    ag0.evento_local()  # [1, 0]
    ag0.evento_local()  # [2, 0]
    vetor_envio = ag0.ao_enviar()  # [3, 0]

    ag1.evento_local()  # [0, 1]
    vetor_recebimento = ag1.ao_receber(vetor_envio)  # max([0,1],[3,0]) + incrementa pos 1 -> [3, 2]

    assert vetor_envio == [3, 0]
    assert vetor_recebimento == [3, 2]

    # O evento de recebimento "aconteceu depois" do envio: domina em toda posicao.
    assert all(vetor_envio[i] <= vetor_recebimento[i] for i in range(2))
