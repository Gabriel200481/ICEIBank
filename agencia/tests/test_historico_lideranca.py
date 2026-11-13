import json

from historico_lideranca import construir_mandatos, imprimir_historico, main


def ev(hora, agencia, tipo, **detalhes):
    return {"agencia": f"agencia-{agencia}", "tipo": tipo, "timestampVetorial": [0, 0, 0],
            "horaParede": f"2026-11-13T00:00:{hora}+00:00", "detalhes": detalhes}


def test_sem_eventos_nao_ha_mandatos():
    assert construir_mandatos([]) == []


def test_ignora_eventos_que_nao_sao_de_eleicao():
    assert construir_mandatos([ev("01.000", 0, "DEPOSITO", id=1)]) == []


def test_novo_lider_registrado_pelas_3_agencias_vira_um_mandato():
    eventos = [ev("01.000", i, "NOVO_LIDER", liderId=2) for i in range(3)]
    mandatos = construir_mandatos(eventos)
    assert len(mandatos) == 1
    assert mandatos[0]["lider"] == 2
    assert mandatos[0]["fim"] is None
    assert mandatos[0]["reconhecidoPor"] == {"agencia-0", "agencia-1", "agencia-2"}


def test_queda_e_reeleicao_encerram_mandato_e_abrem_outro():
    eventos = [
        ev("01.000", 2, "NOVO_LIDER", liderId=2),
        ev("05.000", 1, "LIDER_CAIU", liderId=2, detectadoPor=1),
        ev("05.100", 1, "NOVO_LIDER", liderId=1),
        ev("05.200", 0, "NOVO_LIDER", liderId=1),
    ]
    m = construir_mandatos(eventos)
    assert [x["lider"] for x in m] == [2, 1]
    assert m[0]["motivoFim"] == "QUEDA_DETECTADA"
    assert m[0]["fim"] == "2026-11-13T00:00:05.000+00:00"
    assert m[1]["fim"] is None
    assert m[1]["reconhecidoPor"] == {"agencia-0", "agencia-1"}


def test_lider_antiga_que_volta_abre_novo_mandato():
    eventos = [
        ev("01.000", 2, "NOVO_LIDER", liderId=2),
        ev("05.000", 1, "LIDER_CAIU", liderId=2),
        ev("05.100", 1, "NOVO_LIDER", liderId=1),
        ev("10.000", 2, "NOVO_LIDER", liderId=2),
    ]
    m = construir_mandatos(eventos)
    assert [x["lider"] for x in m] == [2, 1, 2]
    assert m[1]["motivoFim"] == "SUBSTITUIDA"


def test_ordena_por_hora_mesmo_com_eventos_fora_de_ordem():
    eventos = [ev("05.100", 1, "NOVO_LIDER", liderId=1), ev("01.000", 2, "NOVO_LIDER", liderId=2)]
    assert [x["lider"] for x in construir_mandatos(eventos)] == [2, 1]


def test_log_incompleto_queda_sem_novo_lider_deixa_mandato_encerrado():
    eventos = [ev("01.000", 2, "NOVO_LIDER", liderId=2), ev("05.000", 1, "LIDER_CAIU", liderId=2)]
    m = construir_mandatos(eventos)
    assert len(m) == 1 and m[0]["motivoFim"] == "QUEDA_DETECTADA"


def test_queda_de_quem_nao_e_a_lider_atual_e_ignorada():
    eventos = [ev("01.000", 1, "NOVO_LIDER", liderId=1), ev("02.000", 0, "LIDER_CAIU", liderId=2)]
    assert construir_mandatos(eventos)[0]["fim"] is None


def test_conta_eleicoes_antes_do_mandato():
    eventos = [ev("00.100", 0, "ELEICAO_INICIADA"), ev("00.200", 1, "ELEICAO_INICIADA"),
               ev("01.000", 2, "NOVO_LIDER", liderId=2)]
    assert construir_mandatos(eventos)[0]["eleicoesAntes"] == 2


def test_imprimir_sem_mandatos(capsys):
    imprimir_historico([])
    assert "nenhuma lideranca" in capsys.readouterr().out


def test_main_le_pasta_e_imprime_tabela(tmp_path, capsys):
    eventos = [ev("01.000", 2, "NOVO_LIDER", liderId=2), ev("05.000", 1, "LIDER_CAIU", liderId=2)]
    (tmp_path / "eventos-agencia-1.jsonl").write_text("\n".join(json.dumps(e) for e in eventos) + "\n", encoding="utf-8")
    main(["historico_lideranca.py", str(tmp_path)])
    saida = capsys.readouterr().out
    assert "QUEDA_DETECTADA" in saida
    assert "4.0s" in saida
