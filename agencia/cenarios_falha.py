"""Cenarios de falha da Parte D (Sprint 4) com 3 agencias REAIS, cada uma em um
processo separado (uvicorn), sem Docker. Um "supervisor" por agencia imita o
`restart: on-failure` do compose: se o processo sai com erro (queda injetada),
ele sobe de novo, com o mesmo DATA_DIR (o "volume").

Uso (PowerShell, na pasta agencia):   python cenarios_falha.py

Verifica, depois de cada cenario, o invariante: a soma dos saldos nunca muda e
nenhuma reserva fica presa. Sai com codigo 1 se algum cenario falhar.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent
TOKEN = "segredo-de-teste"
H_INT = {"x-token-interno": TOKEN}
URL = {i: f"http://localhost:{4000 + i}" for i in range(3)}
DADOS = Path(tempfile.mkdtemp(prefix="iceibank-cenarios-"))
SALDO_INICIAL = 1000.0


class Agencia:
    def __init__(self, i: int):
        self.i, self.proc, self.falha, self.supervisionada = i, None, "", True
        self.pasta = DADOS / f"agencia-{i}"
        self.pasta.mkdir()
        self.quedas = 0
        self.reentrega = "1"
        threading.Thread(target=self._supervisor, daemon=True).start()

    def _lancar(self):
        env = {
            **os.environ, "AGENCIA_ID": str(self.i), "PORTA_BASE": "4000", "DATA_DIR": str(self.pasta),
            "TOKEN_INTERNO": TOKEN, "FALHA_2PC": self.falha, "HEARTBEAT_INTERVALO": "1",
            "INTERVALO_REENTREGA": self.reentrega, "INTERVALO_RESOLUCAO": "1", "PYTHONUNBUFFERED": "1",
        }
        env.pop("RABBITMQ_URL", None)
        log = open(self.pasta / "saida.log", "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.app:app", "--port", str(4000 + self.i), "--log-level", "warning"],
            cwd=RAIZ, env=env, stdout=log, stderr=log,
        )

    def _supervisor(self):  # restart: on-failure
        while True:
            if self.proc is not None and self.proc.poll() not in (None, 0) and self.supervisionada:
                self.quedas += 1
                self._lancar()
            time.sleep(0.2)

    def subir(self, falha=""):
        self.falha, self.supervisionada = falha, True
        self._lancar()

    def parar(self, supervisionada=False):  # docker compose stop
        self.supervisionada = supervisionada
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(10)

    def eventos(self):
        arq = self.pasta / f"eventos-agencia-{self.i}.jsonl"
        if not arq.exists():
            return []
        return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]

    def tipos(self):
        return [e["tipo"] for e in self.eventos()]


AG = [Agencia(i) for i in range(3)]
JWT = {"Authorization": ""}
FALHOU = []


def esperar(cond, tempo=25, passo=0.3):
    fim = time.time() + tempo
    while time.time() < fim:
        try:
            if cond():
                return True
        except httpx.HTTPError:
            pass
        time.sleep(passo)
    return False


def conta(i):
    return httpx.get(f"{URL[i % 3]}/contas/{i}", headers=JWT, timeout=2).json()


def transferir(origem, destino, valor, via=0):
    return httpx.post(f"{URL[via]}/transferencias", headers=JWT, timeout=20,
                      json={"idOrigem": origem, "idDestino": destino, "valor": valor})


def soma_e_reservas():
    contas = [conta(i) for i in range(3)]
    return sum(c["saldo"] for c in contas), sum(c["reservado"] for c in contas), contas


def lider_ok():
    return all(httpx.get(f"{URL[i]}/bully/lider", timeout=1).json()["liderId"] == 2 for i in range(3))


def tudo_no_ar():
    return all(httpx.get(f"{URL[i]}/saude", timeout=1).status_code == 200 for i in range(3))


def verificar(nome, condicao, detalhe=""):
    print(f"   [{'OK' if condicao else 'FALHOU'}] {nome} {detalhe}")
    if not condicao:
        FALHOU.append(nome)


def invariante(rotulo):
    ok = esperar(lambda: soma_e_reservas()[1] == 0, 30)
    soma, reservas, contas = soma_e_reservas()
    verificar(f"{rotulo}: soma dos saldos == {3 * SALDO_INICIAL} e nenhuma reserva presa", ok and soma == 3 * SALDO_INICIAL,
              f"(soma={soma}, reservas={reservas}, saldos={[c['saldo'] for c in contas]})")


def reiniciar_tudo(reentrega="1"):
    # reentrega alta (60 s) nos cenarios 2 e 3: assim o unico caminho para sair da
    # duvida e o participante CONSULTAR o coordenador (e nao a reentrega dele).
    for a in AG:
        a.parar()
        a.reentrega = reentrega
    for a in AG:
        for marcador in a.pasta.glob("falha-*"):
            marcador.unlink()
    for a in AG:
        a.subir()
    assert esperar(lambda: tudo_no_ar() and lider_ok(), 40), "agencias nao subiram"


def titulo(t):
    print(f"\n=== {t} ===")


try:
    for a in AG:
        a.subir()
    assert esperar(lambda: tudo_no_ar() and lider_ok(), 40), "agencias nao subiram / sem lider 2"
    JWT["Authorization"] = "Bearer " + httpx.post(f"{URL[0]}/auth/login", json={"usuario": "aluno", "senha": "senha123"}).json()["access_token"]
    for i in range(3):
        httpx.post(f"{URL[i]}/contas", headers=JWT, json={"id": i, "nomeAluno": f"Conta{i}", "saldoInicial": SALDO_INICIAL})

    titulo("Base: transferencia entre agencias via 2PC (cliente fala com a 0, lider e a 2)")
    r = transferir(0, 1, 100)
    verificar("200 COMMIT", r.status_code == 200 and r.json()["resultado"] == "COMMIT", str(r.json()))
    verificar("saldos 900/1100", (conta(0)["saldo"], conta(1)["saldo"]) == (900, 1100))
    invariante("base")
    tipos_lider = AG[2].tipos()
    verificar("logs com as duas fases", {"2PC_PREPARAR_ENVIADO", "2PC_DECISAO_COMMIT", "2PC_DECISAO_ENVIADA", "2PC_CONCLUIDA"} <= set(tipos_lider))

    titulo("Abort: saldo insuficiente e conta inexistente, sem efeito residual")
    r = transferir(0, 1, 99999)
    verificar("422 ABORT com motivo", r.status_code == 422 and "Saldo insuficiente" in r.json()["detail"], r.json()["detail"])
    r = transferir(0, 99, 10)
    verificar("422 ABORT (destino 99 inexistente) e debito nao aplicado", r.status_code == 422 and conta(0)["saldo"] == 900)
    invariante("abort")

    titulo("Cenario 1: participante fora do ar na fase 1")
    AG[1].parar()
    r = transferir(0, 1, 50)
    verificar("ABORT por timeout (422)", r.status_code == 422 and "nao respondeu" in r.json()["detail"], r.json()["detail"])
    AG[1].subir()
    esperar(tudo_no_ar, 30)
    esperar(lambda: lider_ok(), 30)
    invariante("cenario 1")

    titulo("Cenario 2: participante cai depois de votar SIM (participante-apos-votar) e antes de responder")
    reiniciar_tudo(reentrega="60")
    AG[1].parar()
    AG[1].subir(falha="participante-apos-votar")
    esperar(tudo_no_ar, 30)
    esperar(lider_ok, 30)
    r = transferir(1, 0, 100)  # a agencia 1 e a do DEBITO: reserva e cai
    verificar("coordenador decide ABORT (timeout conta como NAO)", r.status_code == 422, r.text)
    esperar(lambda: "2PC_RESOLVIDA_POR_CONSULTA" in AG[1].tipos(), 30)
    verificar("agencia 1 caiu e foi reiniciada", AG[1].quedas >= 1, f"(quedas={AG[1].quedas})")
    verificar("agencia 1 resolveu a duvida consultando o coordenador", "2PC_RESOLVIDA_POR_CONSULTA" in AG[1].tipos())
    invariante("cenario 2")

    titulo("Cenario 3: coordenador cai antes de decidir (coordenador-antes-de-decidir)")
    reiniciar_tudo(reentrega="60")
    AG[2].parar()
    AG[2].subir(falha="coordenador-antes-de-decidir")
    esperar(tudo_no_ar, 30)
    esperar(lider_ok, 30)
    r = transferir(0, 1, 100)
    verificar("cliente recebe 503 (coordenador caiu)", r.status_code == 503, r.text)
    esperar(lambda: "2PC_ABORTO_PRESUMIDO" in AG[2].tipos(), 30)
    verificar("coordenador registrou aborto presumido ao voltar", "2PC_ABORTO_PRESUMIDO" in AG[2].tipos())
    invariante("cenario 3")
    verificar("participantes sairam da duvida sem ficar bloqueados", all("2PC_RESOLVIDA_POR_CONSULTA" in AG[i].tipos() for i in (0, 1)))

    titulo("Cenario 4: coordenador cai depois de decidir COMMIT (coordenador-apos-decidir)")
    reiniciar_tudo()
    AG[2].parar()
    AG[2].subir(falha="coordenador-apos-decidir")
    esperar(tudo_no_ar, 30)
    esperar(lider_ok, 30)
    antes = (conta(0)["saldo"], conta(1)["saldo"])
    r = transferir(0, 1, 100)
    verificar("cliente recebe 503, mas a decisao COMMIT ja estava gravada", r.status_code == 503, r.text)
    ok = esperar(lambda: (conta(0)["saldo"], conta(1)["saldo"]) == (antes[0] - 100, antes[1] + 100), 40)
    verificar("a transferencia se completa depois (apesar do 503)", ok, f"(antes={antes}, depois=({conta(0)['saldo']}, {conta(1)['saldo']}))")
    invariante("cenario 4")

    titulo("Cenario 5: o bloqueio do 2PC (coordenador nao volta)")
    reiniciar_tudo()
    AG[2].parar()
    AG[2].subir(falha="coordenador-antes-de-decidir")
    esperar(tudo_no_ar, 30)
    esperar(lider_ok, 30)
    AG[2].supervisionada = False  # "docker compose stop agencia-2" assim que cair
    saldo0 = conta(0)["saldo"]
    r = transferir(0, 1, 100)
    verificar("cliente recebe 503", r.status_code == 503)
    AG[2].proc.wait(15)
    esperar(lambda: "2PC_BLOQUEADA_AGUARDANDO_COORDENADOR" in AG[0].tipos(), 30)
    c0 = conta(0)
    verificar("participante registrou 2PC_BLOQUEADA_AGUARDANDO_COORDENADOR", "2PC_BLOQUEADA_AGUARDANDO_COORDENADOR" in AG[0].tipos())
    verificar("reserva presa: reservado=100 e disponivel = saldo - 100", (c0["reservado"], c0["disponivel"], c0["saldo"]) == (100, saldo0 - 100, saldo0), str(c0))
    time.sleep(3)
    verificar("continua preso depois de varias tentativas (nao decide sozinho)", conta(0)["reservado"] == 100)
    saque = httpx.post(f"{URL[0]}/contas/0/sacar", headers=JWT, json={"valor": saldo0})  # tenta sacar tambem o valor reservado
    verificar("saque que inclui o valor reservado e recusado", saque.status_code == 400, saque.text)
    estado_nos = httpx.get(f"{URL[0]}/2pc/transacoes", headers=H_INT).json()["participacoes"]
    verificar("participante PREPARADO (em duvida)", [p["estado"] for p in estado_nos].count("PREPARADO") == 1)
    AG[2].subir()  # docker compose start agencia-2
    esperar(tudo_no_ar, 30)
    esperar(lider_ok, 30)
    invariante("cenario 5 (apos o coordenador voltar)")
    verificar("bloqueio terminou", conta(0)["reservado"] == 0)
finally:
    for a in AG:
        a.parar()
    print(f"\nLogs e estados em {DADOS}")

print("\nRESULTADO:", "TODOS OS CENARIOS OK" if not FALHOU else f"FALHARAM: {FALHOU}")
sys.exit(1 if FALHOU else 0)
