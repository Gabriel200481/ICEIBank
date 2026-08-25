"""Relogio logico de Lamport.

Tres regras:
1. Antes de qualquer evento local, o processo incrementa seu contador.
2. Ao enviar uma mensagem, o processo incrementa o contador e anexa o valor.
3. Ao receber uma mensagem com timestamp t, o processo ajusta seu contador
   para max(contador_local, t) + 1.
"""

import threading


class RelogioLamport:
    def __init__(self) -> None:
        self.contador = 0
        self._lock = threading.Lock()

    def evento_local(self) -> int:
        with self._lock:
            self.contador += 1
            return self.contador

    def ao_enviar(self) -> int:
        with self._lock:
            self.contador += 1
            return self.contador

    def ao_receber(self, timestamp_recebido: int) -> int:
        with self._lock:
            self.contador = max(self.contador, timestamp_recebido) + 1
            return self.contador
