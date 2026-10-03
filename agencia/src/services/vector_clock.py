"""Relogio vetorial - substitui o relogio de Lamport do Sprint 1.

O relogio de Lamport (um unico contador) garante so uma direcao da
causalidade: se A aconteceu antes de B, timestamp(A) < timestamp(B) - mas
dois timestamps diferentes nao permitem concluir com certeza se os eventos
sao causalmente relacionados ou genuinamente concorrentes.

O relogio vetorial usa um vetor de contadores, um por agencia, com 3 regras:
1. Antes de um evento local, o processo incrementa a propria posicao.
2. Ao enviar uma mensagem, incrementa a propria posicao e anexa o vetor
   inteiro a mensagem.
3. Ao receber uma mensagem com vetor V, para cada posicao i:
   vetor[i] = max(vetor[i], V[i]), e so entao incrementa a propria posicao.

Mantem os mesmos nomes de metodo do RelogioLamport (evento_local, ao_enviar,
ao_receber) de proposito - os controllers do Sprint 1 continuam funcionando
sem alteracao, so trocando qual relogio e instanciado em app.py.
"""

import threading


class RelogioVetorial:
    def __init__(self, id_agencia: int, numero_agencias: int) -> None:
        self.id_agencia = id_agencia
        self.vetor = [0] * numero_agencias
        self._lock = threading.Lock()

    def evento_local(self) -> list[int]:
        with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    def ao_enviar(self) -> list[int]:
        with self._lock:
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)

    def ao_receber(self, vetor_recebido: list[int]) -> list[int]:
        with self._lock:
            for i in range(len(self.vetor)):
                self.vetor[i] = max(self.vetor[i], vetor_recebido[i])
            self.vetor[self.id_agencia] += 1
            return list(self.vetor)
