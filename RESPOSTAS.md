# RESPOSTAS - Sprint 1 (ICEIBank)

## Escolha de linguagem (Seção 2.2)

Linguagem escolhida: **Python 3.13**, com **FastAPI** + **Uvicorn**.

Justificativa: FastAPI oferece tipagem via Pydantic (reduz erros de contrato entre
rotas), documentação automática (`/docs`) que ajuda a testar cada endpoint durante
o desenvolvimento, suporte assíncrono nativo (útil para as chamadas REST entre
agências) e uma curva de configuração baixa comparada a Flask puro para o mesmo
resultado. Esta escolha é mantida do Sprint 1 ao Sprint 4, conforme exigido no
roteiro.

---

## Parte B - Perguntas (Seção 6.4)

**1. Por que o relógio de Lamport usa `max(contador_local, timestampRecebido) + 1` ao receber uma mensagem, em vez de simplesmente adotar o timestamp recebido diretamente?**

Porque o objetivo do relógio é garantir que todo evento causado por uma mensagem
recebida tenha um timestamp *estritamente maior* que o timestamp da mensagem que
o causou (e também maior que qualquer evento que já tenha acontecido localmente
antes). Se o processo simplesmente adotasse o timestamp recebido, dois problemas
apareceriam: (a) o contador poderia andar para trás se o processo já estivesse
"na frente" do remetente, perdendo a ordenação dos próprios eventos locais
anteriores; e (b) o evento de recebimento poderia ficar com o *mesmo* timestamp
da mensagem, violando a regra de que causa deve preceder consequência
(`timestamp(causa) < timestamp(consequência)`). O `max(...) + 1` garante as duas
coisas ao mesmo tempo.

**2. Se a Agência 0 está no evento de contador 10 e recebe uma mensagem com timestamp 3, qual o novo valor do contador da Agência 0? O que isso implica sobre agências que processam muitos eventos rapidamente versus agências mais lentas?**

`max(10, 3) + 1 = 11`. Isso implica que uma agência "adiantada" (que já processou
muitos eventos locais) não recua seu relógio ao receber uma mensagem de uma
agência mais "atrasada" - o relógio de Lamport é monotônico, só anda para
frente. Na prática, agências mais rápidas/ocupadas tendem a manter contadores
sempre mais altos que agências mais lentas, e o timestamp de um evento reflete
mais "quantos eventos aconteceram antes dele, na visão daquele processo" do que
o instante real no relógio de parede - por isso o `horaParede` registrado ao
lado do timestamp de Lamport é útil só para comparação humana, nunca para
decisões do sistema.

**Nota de design:** `RelogioLamport` usa um `threading.Lock` em volta das três
operações (mesmo cuidado citado no roteiro para a versão Java com
`synchronized`). Com Uvicorn em single worker isso não é estritamente
necessário, mas o contador é estado mutável compartilhado entre requisições
concorrentes, então o lock elimina qualquer risco de condição de corrida caso
o processo seja rodado com múltiplos workers/threads no futuro.

---

## Parte D - Perguntas (Seção 8.3)

**1. No trecho `agenciaDestino === idAgencia`, por que a transferência local não precisa da lógica de `ao_enviar()`/`ao_receber()` do relógio de Lamport, enquanto a transferência entre agências precisa?**

Porque `ao_enviar()`/`ao_receber()` só fazem sentido quando existe uma
mensagem cruzando a fronteira entre dois processos diferentes - é o mecanismo
que propaga causalidade de um relógio lógico para outro. Na transferência
local, débito e crédito acontecem dentro do mesmo processo, com acesso direto
ao mesmo `RelogioLamport`; usar `evento_local()` duas vezes já é suficiente
para ordenar os dois eventos entre si, porque não há necessidade de
sincronizar o relógio com o de "outro processo" - só existe um processo
envolvido.

**2. Reproduza a falha conhecida e observe o saldo da conta de origem depois do erro. Ele foi revertido? O que isso significa em termos de consistência do sistema bancário?**

Não, o saldo **não é revertido** (testado com as 3 agências rodando de
verdade: agência 0 com R$100, debitou R$10 numa transferência para a agência
2 derrubada no meio do caminho, resultado HTTP 502, saldo final R$60 - o
valor debitado "sumiu"). Isso significa que o sistema, hoje, não garante
**atomicidade** entre o débito local e o crédito remoto: a operação de
transferência entre agências não é tratada como uma unidade indivisível.
Do ponto de vista de um banco real isso é inaceitável (dinheiro não pode
desaparecer), mas aqui é proposital - o log `TRANSFERENCIA_FALHOU` deixa a
inconsistência visível e rastreável, em vez de escondê-la, para ser corrigida
de verdade no Sprint 4.

**3. Pensando à frente para o Sprint 4: cite duas formas possíveis de corrigir esse problema.**

- **Two-Phase Commit (2PC):** um coordenador pergunta às duas agências
  ("posso debitar?", "posso creditar?") na fase de *prepare*; só depois que
  ambas confirmarem que estão prontas (e com o valor reservado) o coordenador
  manda a fase de *commit*. Se qualquer agência falhar ou não responder no
  prepare, a operação inteira é abortada e nada é aplicado.
- **Saga (compensação):** a transferência é dividida em passos locais
  (debitar na origem, depois creditar no destino), cada um com uma ação de
  compensação equivalente. Se o passo de crédito falhar, a saga executa a
  compensação do passo de débito (estornar o valor na origem)
  automaticamente, em vez de deixar a inconsistência registrada só no log.

---

## Parte E - Perguntas (Seção 10.3)

_A preencher junto com a implementação da Parte E._

---

## Parte F - Autenticação JWT (Seção 11)

### Perguntas (Seção 11.3)

_A preencher junto com a implementação da Parte F._

### Justificativas de design

_A preencher junto com a implementação da Parte F._

---

## Parte G - Frontend (Seção 12)

### Perguntas (Seção 12.3)

_A preencher junto com a implementação da Parte G._

### Justificativas de design

_A preencher junto com a implementação da Parte G._

---

## Funcionalidade adicional (Seção 2.1)

_A preencher junto com a implementação da funcionalidade extra._
