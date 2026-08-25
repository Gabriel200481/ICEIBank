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

Execução real (3 agências simultâneas, contas criadas e depositadas quase ao
mesmo tempo nas 3, seguidas de uma transferência entre agência 0 e 1):

```
[Lamport 1] agencia-0 - CRIAR_CONTA {id: 0, ...}
[Lamport 1] agencia-1 - CRIAR_CONTA {id: 1, ...}
[Lamport 1] agencia-2 - CRIAR_CONTA {id: 2, ...}
[Lamport 2] agencia-0 - DEPOSITO {id: 0, valor: 5, ...}
[Lamport 2] agencia-1 - DEPOSITO {id: 1, valor: 5, ...}
[Lamport 2] agencia-2 - DEPOSITO {id: 2, valor: 5, ...}
[Lamport 3] agencia-0 - TRANSFERENCIA_DEBITO {idOrigem: 0, idDestino: 1, valor: 20}
[Lamport 5] agencia-1 - TRANSFERENCIA_CREDITO_REMOTO {idConta: 1, valor: 20, origemAgencia: 0}
```

**1. O relógio de Lamport garante que, se A aconteceu antes de B causalmente, `timestamp(A) < timestamp(B)`. Ele não garante a volta. O que isso significa na prática quando você vê dois eventos com timestamps diferentes na linha do tempo, mas sem saber se um realmente influenciou o outro?**

Significa que a ordem por timestamp, sozinha, não permite concluir causalidade
- só permite descartá-la em um sentido (se `timestamp(A) > timestamp(B)`, então
A com certeza não foi causado por B). No exemplo acima, `TRANSFERENCIA_DEBITO`
(ts 3, agência 0) e o segundo `DEPOSITO` da agência 2 (ts 2) têm timestamps
diferentes, mas nada na transferência dependeu daquele depósito - são eventos
de processos diferentes que, por coincidência de tempo de execução, ficaram
com timestamps próximos/ordenados sem nenhuma relação causal real entre si. A
linha do tempo por Lamport é útil para reconstruir *uma* ordem total possível
e consistente com a causalidade observada, mas não é a *única* verdade sobre
"o que aconteceu antes do quê" no mundo real.

**2. Baseado no que você observou: o relógio de Lamport, sozinho, seria suficiente para um sistema que precisa distinguir com certeza "A e B são concorrentes" de "A aconteceu antes de B"? Por que isso motiva o relógio vetorial do Sprint 2?**

Não. Os três `CRIAR_CONTA` acima (agências 0, 1 e 2) empataram em `timestamp
1` porque são genuinamente concorrentes - nenhuma agência tinha conhecimento
da existência das outras duas quando processou seu próprio evento. Mas o
Lamport, sozinho, não *prova* isso: ele só permitiu que os três ficassem
empatados porque não havia mensagem entre eles até aquele ponto; se por acaso
o agendamento do SO tivesse feito as chamadas em outra ordem, os três
poderiam ter saído com timestamps 1, 2 e 3 sem que isso significasse relação
causal alguma entre eles - um observador não teria como diferenciar esse caso
de uma cadeia causal real de três eventos em série só olhando os números.
É exatamente essa ambiguidade que motiva o relógio vetorial: em vez de um
único contador, cada processo mantém um vetor com o contador de *todos* os
processos que conhece, permitindo comparar dois timestamps e concluir com
certeza matemática se um evento aconteceu-antes do outro, depois-de, ou se
são concorrentes (quando nenhum vetor domina o outro em todas as posições).

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
