# RESPOSTAS - Sprint 1 (ICEIBank)

## Declaração de uso de IA

Este sprint foi implementado com apoio extensivo do **Claude Code** (Anthropic)
— não se limitou a rascunhos ou revisão pontual: a maior parte do código
(backend Python/FastAPI, frontend, testes automatizados, workflow de Git/GitHub
e este próprio arquivo de respostas) foi gerada com a IA, sob minha supervisão
e direção, revisando cada Parte antes de seguir para a próxima. Isso vai além
do "apoio a rascunhos" citado na nota de transparência do roteiro, então
deixo isso explícito aqui em vez de subdeclarar o uso.

Antes de entregar, revisei o código gerado e sou capaz de explicar e defender
as decisões de arquitetura registradas neste arquivo (particionamento,
relógio de Lamport, a limitação conhecida da Parte D, a separação de
mecanismos de autenticação da Parte F, a escolha de funcionalidade adicional).
Qualquer trecho específico que eu não conseguir explicar em uma arguição não
deveria ter sido entregue como meu - assumo essa responsabilidade.

---

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

### Justificativas de design

**Formato das credenciais:** login por `usuario`/`senha` (`POST /auth/login`).
Optei por um usuário de demonstração fixo (`aluno` / `senha123`), em memória,
porque o roteiro não pede uma tabela de usuários/cadastro no Sprint 1 - o
objetivo desta parte é o mecanismo de autenticação (emissão, validação,
expiração, proteção de rota), não um sistema de identidade completo. Criar um
cadastro de usuários "de mentira" só para ter uma tabela pareceria mais
completo, mas seria complexidade sem função real neste sprint.

**Tempo de expiração:** 15 minutos (`JWT_EXPIRACAO_MINUTOS`, configurável por
variável de ambiente). Curto o suficiente para limitar a janela de uso de um
token vazado, longo o suficiente para não expirar no meio de uma sessão
normal de uso do frontend.

**A chamada `creditar-remoto` (agência-a-agência) usa um mecanismo diferente
do JWT do frontend.** Implementei um **service token** - um segredo
compartilhado entre as 3 agências (`AGENCIA_SERVICE_TOKEN`, mesmo valor
porque é o mesmo código-fonte rodando 3 vezes), enviado no cabeçalho
`Authorization: Service <token>` (prefixo diferente de `Bearer`, para deixar
explícito na própria requisição que se trata de um mecanismo distinto).

Justificativa: a chamada `creditar-remoto` não é feita "em nome" de nenhum
usuário logado - é uma chamada de sistema-para-sistema, disparada pela
agência de origem depois que ela já validou o JWT do usuário que pediu a
transferência. Usar o mesmo JWT de usuário nessa chamada teria dois
problemas: (1) o JWT do usuário representa uma sessão pessoal com expiração
pensada para uso interativo - não faz sentido semântico "logar" uma agência
como se fosse um aluno; e (2) precisaria repassar o token do usuário adiante
de processo em processo, acoplando a validade da transferência interna à
sessão daquele usuário especificamente (se o token dele expirasse um segundo
depois do débito, o crédito remoto falharia por um motivo que não tem nada a
ver com a operação em si). Um token de serviço fixo, validado
independentemente do usuário, separa claramente "quem está autorizado a usar
a API" (usuário com JWT) de "quem está autorizado a falar com outra agência"
(a própria infraestrutura do ICEIBank).

### Perguntas (Seção 11.3)

**1. Qual a diferença entre autenticação e autorização? Sua implementação verifica só uma das duas, ou as duas? Um usuário autenticado consegue sacar de uma conta que não é dele?**

Autenticação é confirmar *quem* está fazendo a requisição (o token é válido e
não expirou → é realmente o portador de uma sessão legítima). Autorização é
decidir *o que* esse usuário específico tem permissão de fazer. A
implementação atual só cobre autenticação: `exigir_usuario_autenticado`
verifica que existe um JWT válido, mas não checa se o `sub` do token (o
usuário logado) é "dono" da conta que está sendo movimentada. Na prática,
hoje, **sim**: qualquer usuário autenticado com o único login de demonstração
consegue sacar/depositar/consultar qualquer conta da agência, porque não há
vínculo entre conta e usuário no modelo de dados deste sprint. Isso é uma
limitação real e conhecida - resolvê-la exigiria um modelo de "dono da
conta" e uma checagem de autorização por conta, que ficou fora do escopo
aqui (o roteiro pede autenticação, não um controle de acesso por
titularidade).

**2. Por que o servidor não precisa consultar um banco de dados para validar a assinatura de um JWT a cada requisição? Implicações para escalabilidade?**

Porque a validade do token é verificável matematicamente com a própria chave
secreta (HMAC-SHA256, `jwt.decode`): o servidor recalcula a assinatura a
partir do payload e da chave e compara com a assinatura recebida - se
baterem, o conteúdo não foi alterado desde que o próprio servidor o assinou
no login. Isso significa que qualquer instância da agência (ou, no limite,
qualquer serviço que conheça a mesma `SECRET_KEY`) pode validar o token
sozinha, sem round-trip a um banco ou a um serviço de sessão central. Para
escalabilidade isso é uma vantagem grande: elimina um ponto de contenção
(consulta de sessão a cada requisição) e permite escalar horizontalmente sem
compartilhar estado de sessão entre instâncias - o preço pago é que revogar
um token individual antes do prazo de expiração não é trivial (não há uma
tabela de sessões para apagar uma linha).

**3. O que aconteceria com a segurança do sistema se a chave secreta usada para assinar o JWT vazasse?**

Qualquer pessoa de posse da chave conseguiria forjar tokens válidos para
qualquer usuário (inclusive usuários que não existem), passando por
autenticada em qualquer rota protegida - a garantia inteira do JWT depende do
segredo permanecer secreto. Seria equivalente a vazar a senha mestra do
sistema. A mitigação é rotacionar a chave imediatamente (invalidando de uma
vez todos os tokens já emitidos, inclusive os legítimos, o que forçaria todo
mundo a logar de novo) e, estruturalmente, nunca commitar a chave no
repositório - por isso `JWT_SECRET` é lido de variável de ambiente, com um
valor padrão claramente marcado como "de desenvolvimento" no código.

---

## Parte G - Frontend (Seção 12)

### Justificativas de design

Frontend em HTML/CSS/JavaScript puro (sem framework/build step), servido por
`python -m http.server`. Optei por isso em vez de React/Vue/Angular porque o
roteiro permite explicitamente e o escopo é pequeno (5 formulários, sem
roteamento) - um framework completo seria complexidade sem retorno aqui.

O token fica em `localStorage` (chave `iceibank_token`), a escolha mais
simples possível para persistir a sessão entre reloads da página sem exigir
um backend de sessão. A troca de agência é um `<select>` no topo da página
com as 3 URLs conhecidas (`localhost:4000-4002`), lido a cada requisição
(`Api.baseUrl()`) - o frontend não faz nenhuma suposição sobre qual agência é
"a certa", quem decide isso é sempre o backend (particionamento).

### Perguntas (Seção 12.3)

**1. Como o frontend "lembra" de reenviar o token em cada requisição depois do login?**

O token retornado pelo `/auth/login` é salvo em `localStorage` (objeto
`Sessao`). Toda chamada à API passa pela função central `Api.chamar()`, que
monta o header `Authorization: Bearer <token>` automaticamente a partir do
`localStorage` antes de cada `fetch` - as telas individuais (saldo, depósito,
transferência) não precisam se preocupar com autenticação, só chamam
`Api.chamar(caminho, opcoes)`.

**2. Se o token expirar enquanto alguém está usando o frontend no meio de uma operação, o que acontece na sua implementação? A interface avisa a pessoa usuária, ou ela só vê um erro genérico?**

A interface avisa de forma específica, não genérica. `Api.chamar()` trata o
status 401 como um caso à parte: limpa a sessão salva, devolve a tela de
login automaticamente e lança um erro com a mensagem
`"Sessao encerrada (<motivo>). Faca login novamente."`, usando o `detail`
que a API devolveu (ex.: "Token expirado."). Testado na prática subindo o
backend com `JWT_EXPIRACAO_MINUTOS=0`: qualquer ação após o login volta para
a tela de login com essa mensagem, em vez de travar num erro silencioso.

**3. Esta unidade trata de arquitetura MVC. No seu frontend, onde fica o "M", o "V" e o "C"? Eles existem de forma clara, ou o código ficou mais misturado do que o padrão sugere?**

Em `app.js` a separação é explícita, nomeada nos próprios comentários:
`Sessao`/`Api` fazem o papel de **Model** (estado da sessão e acesso a
dados), `Vista` é a **View** (toda leitura/escrita do DOM está concentrada
ali) e `Controlador` é o **Controller** (liga os eventos de formulário às
chamadas de `Api` e decide o que `Vista` deve mostrar em seguida). Dito
isso, a separação é mais informal do que num framework MVC de verdade: não
há um mecanismo de binding ou de eventos entre as camadas, é só
`Controlador` chamando `Vista` e `Api` diretamente por importação de objeto
global (sem módulos ES/build step) - ou seja, a fronteira existe e é
identificável, mas é mantida por convenção/disciplina do código, não
imposta pela estrutura da aplicação como aconteceria com um framework.

---

## Funcionalidade adicional (Seção 2.1)

**Escolhida:** rota de status/health-check por agência (`GET /status`),
retornando o relógio de Lamport atual e a quantidade de contas sob
responsabilidade daquela agência.

```json
{"idAgencia": 2, "timestampLamportAtual": 2, "quantidadeContas": 2}
```

**Por que essa:** entre as opções sugeridas no roteiro, essa foi a que mais
diretamente serve para *observar* o próprio sistema distribuído que o sprint
constrói - dá pra consultar, de fora, "em que ponto do relógio lógico cada
agência está agora" sem precisar ler o `.jsonl` ou rodar `mesclar_logs.py`.
Também é a base natural para health-checks de infraestrutura (ex.: um
orquestrador decidindo se uma agência está "viva" e respondendo).

**Decisão de design:** ao contrário das demais rotas, `/status` **não exige**
JWT. Justificativa: um health-check precisa ser alcançável por ferramentas de
monitoramento/infraestrutura que não têm (nem deveriam precisar de) uma
sessão de usuário - exigir login para saber se o serviço está no ar
inverteria a lógica de um endpoint de saúde. Como a rota não expõe dados de
nenhuma conta específica (só um contador agregado), o risco de vazar
informação sensível é baixo.

**Evidência:** testado end-to-end com servidor real (agência 2, porta 4002):
contador de Lamport e quantidade de contas em 0 antes de qualquer operação;
após criar 2 contas, `/status` passou a reportar `timestampLamportAtual: 2` e
`quantidadeContas: 2`, chamando a rota sem nenhum header de autenticação.

---

# RESPOSTAS - Sprint 2 (ICEIBank)

A declaração de uso de IA feita no Sprint 1 continua valendo integralmente
para este sprint - mesma ferramenta (Claude Code), mesmo nível de uso
extensivo sob minha supervisão e revisão, mesma responsabilidade assumida de
entender e defender qualquer trecho entregue.

## Escolha de linguagem (Seção 2.2)

Mantida a mesma do Sprint 1: **Python 3.13 + FastAPI + Uvicorn**, conforme
exigido (a entrega evolui o mesmo código, não recomeça do zero).

## RabbitMQ local vs. CloudAMQP

O roteiro recomenda CloudAMQP (gerenciado). Durante o desenvolvimento deste
sprint usei um RabbitMQ local via Docker (`rabbitmq:3-management`) - a
própria seção 4.1 do roteiro cita essa alternativa para quem não tem
internet confiável durante a aula. A aplicação não faz nenhuma distinção
entre as duas: tudo depende só do valor de `RABBITMQ_URL`, então trocar para
uma instância CloudAMQP real é só redefinir essa variável de ambiente, sem
mudar nenhuma linha de código.

## Parte B - Relógio vetorial (Seção 6)

### Decisão de design

O roteiro permite apagar `lamport_clock.py` ou mantê-lo para consulta -
optei por **apagar** (junto com seu teste), já que o Sprint 2 substitui
completamente o relógio de Lamport pelo vetorial em todos os pontos onde ele
era usado (controllers, event log, rota de status). Manter um arquivo morto,
sem nenhum import apontando pra ele, só adicionaria confusão sobre qual
relógio está realmente em uso - o histórico do Git já preserva o código do
Sprint 1 para quem quiser consultar.

`RelogioVetorial` mantém os mesmos nomes de método do `RelogioLamport`
(`evento_local`, `ao_enviar`, `ao_receber`) de propósito: os controllers de
contas e transferências do Sprint 1 não precisaram de nenhuma alteração para
passar a usar o vetor - só a instanciação em `app.py` mudou. Os pontos que
dependiam do formato antigo (um único inteiro) - o payload do
`creditar-remoto` e a rota `/status` - foram atualizados para carregar o
vetor completo (`timestampVetorial` em vez de `timestampLamport`,
`timestampVetorialAtual` em vez de `timestampLamportAtual`).

### Perguntas (Seção 6.4)

**1. Com 3 agências o vetor tem 3 posições. Se o sistema crescesse para 10 agências, o que aconteceria com o tamanho de cada vetor anexado a cada mensagem? Isso é um problema?**

O vetor cresceria para 10 posições, e esse tamanho é anexado a **toda**
mensagem publicada e a **todo** evento gravado no log - o overhead cresce
linearmente com o número de processos (agências) no sistema, não com o
número de eventos. Para o ICEIBank, com um número pequeno e fixo de
agências, isso não é um problema real: 10 inteiros a mais por mensagem é
desprezível perto do resto do payload (JSON, cabeçalhos HTTP/AMQP). Vira um
problema de verdade em sistemas com milhares de processos (ex.: um cluster
grande, ou dispositivos móveis entrando e saindo constantemente) - cada
mensagem carregaria milhares de inteiros só de metadado de causalidade. É
exatamente essa limitação de escala que motiva variantes mais compactas
(relógios de matriz, "vector clocks" podados, ou abordagens baseadas em
versão/intervalo) em sistemas distribuídos de grande porte - fora do escopo
deste sprint, mas é a direção natural do problema.

**2. Dado V1 = [3, 1, 0] e V2 = [3, 2, 0]: qual evento aconteceu primeiro, ou eles são concorrentes?**

`V1` aconteceu **antes** de `V2`. Comparando posição a posição: `3<=3`,
`1<=2`, `0<=0` - `V1` é menor ou igual a `V2` em todas as posições (e são
diferentes), então `V1 <= V2` vale integralmente, o que caracteriza a
relação "aconteceu-antes".

**3. Dado V1 = [3, 1, 0] e V2 = [1, 3, 0]: qual evento aconteceu primeiro, ou eles são concorrentes?**

São **concorrentes**. Na posição 0, `V1[0]=3 > V2[0]=1` (então `V2 <= V1` já
não vale nessa posição); na posição 1, `V1[1]=1 < V2[1]=3` (então `V1 <= V2`
já não vale nessa posição). Como nem `V1 <= V2` nem `V2 <= V1` é verdade em
todas as posições simultaneamente, nenhum dos dois domina o outro - não há
como um ter influenciado o outro causalmente, então são concorrentes por
definição.

---

## Parte C - Publish/Subscribe entre agências (Seção 7)

### Decisões de design

A chamada REST direta `/contas/{id}/creditar-remoto` do Sprint 1 foi
**removida** - não há mais nenhuma rota HTTP equivalente. O crédito remoto
chega exclusivamente via mensageria: `transferenciasController.transferir`
publica na exchange `iceibank.eventos` (routing key `agencia.<id>.creditar`)
e cada agência consome sua própria fila (`fila-agencia-<id>`) numa thread
dedicada, iniciada junto com o servidor HTTP em `app.py`
(`mensageria.assinar`).

Como consequência, o **service token** do Sprint 1 (usado para proteger a
chamada agência-a-agência) também deixou de fazer sentido e foi removido
(`exigir_token_de_servico`, `SERVICE_TOKEN`) - não existe mais nenhuma
chamada HTTP entre agências para proteger. A proteção que existia nesse
nível simplesmente não tem mais onde se aplicar; a pergunta 3 abaixo discute
o que isso implica para a segurança do novo mecanismo.

Para manter os testes rápidos e sem depender de infraestrutura externa, a
função `criar_app()` ganhou um parâmetro `iniciar_consumidor` (default
`True`): os testes de controller usam `False` e simulam a entrega da
mensagem diretamente (chamando a função de processamento exposta em
`app.state.processar_credito_recebido`), enquanto um arquivo separado
(`tests/test_mensageria.py`) valida `publicar()`/`assinar()` de ponta a
ponta contra um broker RabbitMQ real (pulado automaticamente se
`RABBITMQ_URL` não estiver definida).

### Evidência do teste de resiliência (executado de verdade)

Com a Agência 1 derrubada (processo encerrado) depois de já ter criado a
conta 1 e já ter consumido um primeiro crédito (saldo 30), uma segunda
transferência para ela ainda retornou **200 OK** (mensagem publicada
normalmente - a fila `fila-agencia-1`, já existente de quando a agência
rodou antes, reteve a mensagem). Ao subir a Agência 1 de novo, o log gerado
foi:

```
CRIAR_CONTA            {id: 1, saldoInicial: 0}
TRANSFERENCIA_CREDITO_REMOTO  {idConta: 1, valor: 30}   <- aplicado antes da queda
CREDITO_REMOTO_FALHOU  {idConta: 1, valor: 20, motivo: "conta nao encontrada"}  <- apos reiniciar
```

### Perguntas (Seção 7.5)

**1. O que aconteceu exatamente quando a Agência 1 voltou? A mensagem foi aplicada? Por quê?**

A mensagem **não foi perdida** - ela chegou e foi processada (o log mostra
isso explicitamente, com `CREDITO_REMOTO_FALHOU`), mas o crédito **não foi
aplicado**, porque a conta 1 não existia mais: as contas vivem só em memória
(um `dict` dentro do processo), e reiniciar o processo apaga esse estado por
completo. A mensagem sobreviveu à queda da agência graças à fila *durable*
do RabbitMQ; o que não sobreviveu foi o estado da aplicação que deveria
recebê-la. São dois problemas de durabilidade completamente diferentes, e a
mensageria só resolve um dos dois.

**2. Compare com o Sprint 1: o que melhorou, e o que continua em aberto?**

Melhorou a **durabilidade da comunicação**: no Sprint 1, se a agência de
destino estivesse fora do ar no exato momento da chamada REST, a mensagem
simplesmente nunca existia - era uma falha de rede imediata, sem nenhum
registro de intenção em lugar nenhum além do log de erro da origem. Agora, a
intenção ("creditar a conta X em Y") fica registrada de forma durável no
broker até alguém processá-la, mesmo que ninguém esteja ouvindo no momento
exato da publicação.

O que continua em aberto é a **consistência do estado da aplicação**: "a
mensagem não se perde" é uma garantia sobre o transporte, não sobre o
sistema como um todo. Se o estado que a mensagem precisa encontrar (a conta)
também não for durável, a entrega da mensagem deixa de ser suficiente - o
problema só migra de "a chamada falhou" (Sprint 1) para "a mensagem chegou,
mas não encontrou onde aplicar o valor" (Sprint 2). Resolver isso de verdade
exigiria persistência das contas em disco/banco, o que também está fora do
escopo deste sprint.

**3. O consumidor de mensagens não passa por nenhuma verificação de JWT. Isso é um problema de segurança?**

Sim, é um problema de segurança real, não hipotético. No ambiente de
desenvolvimento deste sprint, qualquer processo com acesso à
`RABBITMQ_URL` (que é só uma variável de ambiente, sem controle de acesso
por routing key) consegue publicar uma mensagem na exchange
`iceibank.eventos` com qualquer routing key `agencia.<id>.creditar` e
qualquer payload - e o consumidor aplica o crédito sem checar quem publicou
nem se a origem alegada (`origemAgencia`) é verdadeira. Isso é
qualitativamente diferente do Sprint 1: lá, pelo menos a rota REST exigia um
token (ainda que fosse só um segredo compartilhado fixo); aqui, não existe
nenhuma verificação equivalente no caminho da mensageria.

Em produção isso seria mitigado por controle de acesso no próprio broker
(usuários/permissões por vhost ou por exchange no RabbitMQ, TLS mútuo,
credenciais por agência em vez de uma única `RABBITMQ_URL` compartilhada) -
nada disso foi implementado aqui porque está fora do escopo do roteiro deste
sprint, mas é uma lacuna real que eu identifico conscientemente, não um
descuido que passou despercebido.

---

## Parte D - Linha do tempo causal (Seção 8)

### Evidência (execução real)

Com as 3 agências rodando, criei uma conta em cada uma **quase ao mesmo
tempo** (3 chamadas disparadas em paralelo, sem nenhuma relação entre elas)
e, em seguida, fiz uma transferência real entre a Agência 0 e a Agência 1.
Saída real do `mesclar_logs.py`:

```
=== Linha do tempo (ordenada por hora de parede) ===
[agencia-0] vetor=[1, 0, 0] CRIAR_CONTA {id: 0, ...}
[agencia-1] vetor=[0, 1, 0] CRIAR_CONTA {id: 1, ...}
[agencia-2] vetor=[0, 0, 1] CRIAR_CONTA {id: 2, ...}
[agencia-0] vetor=[2, 0, 0] TRANSFERENCIA_DEBITO {idOrigem: 0, idDestino: 1, valor: 30}
[agencia-1] vetor=[3, 2, 0] TRANSFERENCIA_CREDITO_REMOTO {idConta: 1, valor: 30, origemAgencia: 0}

=== Pares de eventos CONCORRENTES entre agencias diferentes ===
[agencia-0] CRIAR_CONTA ([1,0,0])  x  [agencia-1] CRIAR_CONTA ([0,1,0])
[agencia-0] CRIAR_CONTA ([1,0,0])  x  [agencia-2] CRIAR_CONTA ([0,0,1])
[agencia-1] CRIAR_CONTA ([0,1,0])  x  [agencia-2] CRIAR_CONTA ([0,0,1])
[agencia-1] CRIAR_CONTA ([0,1,0])  x  [agencia-0] TRANSFERENCIA_DEBITO ([2,0,0])
[agencia-2] CRIAR_CONTA ([0,0,1])  x  [agencia-0] TRANSFERENCIA_DEBITO ([2,0,0])
[agencia-2] CRIAR_CONTA ([0,0,1])  x  [agencia-1] TRANSFERENCIA_CREDITO_REMOTO ([3,2,0])
```

Os 3 `CRIAR_CONTA` (uma por agência, sem relação entre si) apareceram
corretamente como concorrentes **dois a dois**. O par
`TRANSFERENCIA_DEBITO`/`TRANSFERENCIA_CREDITO_REMOTO` - que tem relação
causal real, o crédito só existe porque o débito aconteceu - **não**
apareceu na lista de concorrentes, exatamente como esperado: `[2,0,0] <=
[3,2,0]` em toda posição, então o script classifica como `ANTES`, não
`CONCORRENTES`.

### Perguntas (Seção 8.3)

**1. O que, no relógio vetorial, torna essa comparação confiável (o Lamport do Sprint 1 não permitia)?**

O relógio de Lamport colapsa toda a história causal de um processo num
único número - dois eventos com timestamps diferentes podem ter qualquer
relação (causal ou não), porque o número sozinho não guarda *de onde* veio
cada incremento. O vetor, em vez disso, guarda o progresso de **cada**
processo separadamente: a posição `i` do vetor é, literalmente, "quantos
eventos da Agência `i` eu já presenciei (diretamente ou por tabela
repassada numa mensagem)". Por isso dá para comparar posição a posição e
provar causalidade (ou a ausência dela) com certeza, em vez de só inferir a
partir de uma ordem total artificial.

**2. Encontre um par concorrente real no seu teste - faz sentido eles não terem relação causal?**

Sim. O par `[agencia-1] CRIAR_CONTA ([0,1,0])` x `[agencia-2] CRIAR_CONTA
([0,0,1])` faz todo sentido como concorrente: são duas chamadas HTTP
completamente independentes, disparadas em paralelo contra agências
diferentes, sem nenhuma mensagem trocada entre a Agência 1 e a Agência 2 em
momento nenhum desse teste. Nenhum vetor "sabe" da existência do outro -
`[0,1,0]` não domina `[0,0,1]` (a posição 2 de um é maior que a do outro, e
vice-versa na posição 1) -, então a classificação como concorrente é
exatamente o que se espera fisicamente do cenário.

**3. O algoritmo é O(n²) - seria um problema em escala? O que se poderia fazer?**

Para o volume deste projeto (algumas dezenas de eventos por execução de
teste), O(n²) é irrelevante - a comparação roda em milissegundos. Em um
sistema real com milhões de eventos, comparar todos os pares se tornaria
inviável (um milhão de eventos já são ~5×10¹¹ comparações). Algumas
direções possíveis para tornar isso escalável: (a) restringir a comparação
a janelas de tempo (só comparar eventos próximos no tempo de parede,
assumindo que eventos muito distantes raramente são o par concorrente que
interessa observar), (b) indexar eventos por posição do vetor e usar
estruturas específicas para consulta de dominância parcial em vez de força
bruta, ou (c) processar isso de forma incremental/streaming conforme os
eventos chegam, em vez de recarregar e comparar tudo do zero a cada
execução - cada evento novo só precisaria ser comparado contra os eventos
"recentes" ainda relevantes, não contra todo o histórico.

---

## Funcionalidade adicional - Sprint 2 (Seção 2.1)

**Escolhida:** fila de auditoria (`agencia/auditoria.py`) - um consumidor
extra, independente das 3 agências, que escuta **todos** os créditos
publicados por qualquer uma delas e mantém um log central
(`agencia/data/auditoria.jsonl`).

**Por que essa:** entre as opções sugeridas, essa foi a que mais
diretamente explora um recurso do RabbitMQ que o resto da implementação não
usa - as filas de cada agência se ligam à exchange com a *routing key*
**exata** delas (`agencia.0.creditar`, por exemplo), então só recebem
mensagens destinadas a si mesmas. A fila de auditoria se liga com um
**padrão coringa** (`agencia.*.creditar`), recebendo uma cópia de toda
mensagem de crédito publicada, de qualquer agência, sem interferir no
roteamento normal - a exchange topic entrega a mesma mensagem para cada
fila cuja *routing key* bate com ela, então a agência de destino recebe a
sua cópia normalmente e a auditoria recebe a dela, de forma independente.

**Como usar:** roda como um processo separado, em paralelo às 3 agências:

```powershell
cd agencia
python auditoria.py
```

**Evidência:** testado end-to-end com 2 agências reais rodando + o
`auditoria.py` como terceiro processo. Uma transferência entre agências
(conta 0 → conta 1, valor 35) gerou, no arquivo `auditoria.jsonl`, o
registro `{"horaAuditoria": "...", "mensagem": {"idConta": 1, "valor": 35.0,
"vetorEnvio": [3,0,0], "origemAgencia": 0}}` - capturado de forma
independente do processamento normal feito pela Agência 1.

---

# RESPOSTAS - Sprint 3 (ICEIBank)

## Declaração de uso de IA

A declaração dos sprints anteriores continua valendo: o **Claude Code** (Anthropic) implementou a maior parte deste sprint (backend Python, app Flutter, testes, evidências e este arquivo) sob minha direção e revisão. Sou responsável por entender e defender qualquer trecho entregue; o que eu não conseguir explicar não deveria ter sido entregue como meu.

## Escolha de linguagem e stack

Mantidos **Python 3.13 + FastAPI** no backend (a seção 11 do roteiro permite adaptar o Bully para Python: `httpx` com `timeout=1`, `threading.Lock` no estado compartilhado, thread para o heartbeat). O app é **Flutter** (`http`, `shared_preferences`, `connectivity_plus`). Para o armazenamento local escolhi `shared_preferences` (chave-valor em arquivo) em vez de `sqflite`/`Hive`: o estado a guardar é pequeno (uma conta e uma fila curta), e isso evita um plugin nativo que dificultaria os testes. A persistência fica atrás de uma interface (`ArmazenamentoLocal`), então trocar por SQLite não mexe no resto.

## Decisões de design

- **Bully:** uma agência só pergunta aos IDs **maiores**; se nenhum responde, ela é a maior viva, assume e avisa todas. Se algum responde, esse assume a eleição e a agência espera o `coordenador`; se ele não anunciar a tempo (caiu no meio), ela recomeça. Só uma eleição por vez por agência, para a "tempestade" inicial não multiplicar trabalho.
- **Heartbeat:** uma thread consulta `GET /bully/lider` da líder a cada `HEARTBEAT_INTERVALO` (2 s) com timeout de 1 s; só reelege após `HEARTBEAT_FALHAS` (2) falhas seguidas. A líder não faz heartbeat de si mesma.
- **Rotas de Bully sem JWT:** são chamadas entre agências, não de usuário (mesmo raciocínio do consumidor de mensagens do Sprint 2).
- **Sincronização, uma operação por chamada:** o app envia a fila em ordem; cada operação leva o `vetorBase` (versão da conta que o app viu). Dentro da mesma sincronização, a operação seguinte usa a versão devolvida pela anterior, porque depende causalmente dela.
- **Quando é conflito:** `vetorBase` igual ou depois da versão da conta → aplica; **antes** (o servidor evoluiu) ou **concorrente** → HTTP 409, sem aplicar e devolvendo o estado atual.
- **Offline-first só para depósito e saque.** Transferência exige conexão: mexe em duas contas, possivelmente em agências diferentes, e o mecanismo de sincronização trata uma conta por operação.
- **Evidências:** prints `.png` reais de terminal e do app em emulador, em `evidencias/sprint3/` (ver a seção "Evidências" abaixo).

## Parte A - Perguntas (Seção 5.5)

**1. Por que o Bully elege o de maior ID e não o de menor? O resultado seria diferente se a regra fosse invertida?**

A regra "maior ID" não tem valor especial: o que o algoritmo precisa é de uma **ordem total conhecida por todas as agências**, para decidir quem vence sem negociar nem trocar votos. O ID já é essa ordem. Se invertêssemos (perguntar só aos IDs **menores** e vencer o menor vivo), o algoritmo continuaria correto e com o mesmo custo; só mudaria *quem* vira líder (a agência 0 em vez da 2). A convenção do maior ID vem do artigo original (Garcia-Molina, 1982), em que o ID costuma refletir a prioridade ou capacidade do nó. O que não pode é a regra ser **diferente entre agências** (uma usando maior, outra menor): aí não haveria convergência.

**2. Mais de uma agência declarar líder na subida é bug ou comportamento esperado?**

No meu código o evento se chama `NOVO_LIDER` (o roteiro usa `TORNOU_LIDER`/`LIDER_ANUNCIADO`). No teste real (`evidencias/sprint3/eleicao-inicial.txt`) as três agências registraram `ELEICAO_INICIADA` (a "tempestade"), mas **só a agência 2 se declarou líder por conta própria**; as agências 0 e 1 registraram `NOVO_LIDER {liderId: 2}` ao *receber* o coordenador. Então, nesta execução, nenhuma agência se declarou líder indevidamente. Mas se uma agência de ID menor sobe sozinha (as maiores ainda fora do ar), ela **vai** se declarar líder, e será substituída quando a maior subir. Isso é esperado, não é bug: cada agência decide com a informação que tem naquele instante, e o Bully garante **convergência final**, não ausência de líderes intermediários. Seria bug se o estado final divergisse, e as três consultas a `/bully/lider` devolveram a mesma líder. O `failover-heartbeat.txt` mostra o caso intermediário: a agência 1 foi líder por ~8 s enquanto a 2 estava fora e foi substituída quando a 2 voltou.

**3. `/bully/eleicao` sem autenticação é um problema de segurança real?**

É real, com gravidade limitada neste sprint. Qualquer processo que alcance a porta pode disparar eleições em sequência (tráfego e logs à toa) e, pior, chamar `/bully/coordenador` com um `liderId` qualquer: `receber_coordenador` aceita o anúncio sem verificar quem enviou nem se o ID faz sentido. Uma agência falsa conseguiria fazer as outras acreditarem em uma líder errada até o próximo heartbeat/eleição corrigir. Hoje a líder é só informativa, então o dano é pequeno; no Sprint 4, quando ela coordenar o 2PC, passa a ser grave. A mitigação seria rede privada mais autenticação entre serviços (mTLS ou token de serviço). Aqui é uma limitação assumida.

*Complemento (custo e JWT).* No pior caso (a de menor ID inicia), cada agência que responde dispara a própria eleição para as maiores, o que dá algo da ordem de **O(n²)** mensagens mais `n-1` de `coordenador`; com 3 agências é desprezível. As rotas de Bully não usam JWT porque o JWT identifica um **usuário** e quem chama é outra agência (mesmo raciocínio do consumidor de mensagens do Sprint 2).

## Parte B - Perguntas (Seção 6.4)

**1. Heartbeat muito curto (100 ms) ou muito longo (60 s)?**

Com 100 ms, cada agência faria ~10 consultas por segundo à líder só para saber se ela está viva, e qualquer lentidão passageira (GC, pico de CPU) viraria falsa queda: reeleições em cascata (*flapping*), rede e logs sobrecarregados. Com 60 s, o custo de rede é quase nulo, mas depois de uma queda as agências ficariam até ~60 s (no meu código, mais de 2 minutos, pois exijo 2 falhas seguidas) acreditando em uma líder morta. Usei intervalo de 2 s (`HEARTBEAT_INTERVALO`), timeout de 1 s e **2 falhas seguidas** (`HEARTBEAT_FALHAS`) antes de reeleger, então uma única resposta lenta não derruba a líder. No teste real (intervalo 1 s) a queda foi derrubada às 21:09:08 e detectada (`LIDER_CAIU`) ~1-2 s depois (`failover-heartbeat.txt`). O falso positivo aqui não corrompe dados (a reeleição é segura), só gera troca de líder e tráfego à toa.

**2. A agência que volta "toma" a liderança de volta. Isso é desejável?**

Foi o que aconteceu: a agência 2 voltou às 21:09:15 e, às ~21:09:17, já era líder de novo (o mandato da agência 1 durou 7,9 s, ver `historico-lideranca.txt`). É consequência do Bully (a eleição inicial de quem sobe é *preemptiva*): a regra é simples e determinística, mas a troca acontece mesmo com a líder atual funcionando bem. O problema prático aparece quando a líder tem trabalho em andamento: no Sprint 4, se a líder muda entre o `PREPARE` e o `COMMIT` de um 2PC, a transação perde o coordenador, e a agência que acabou de subir não conhece a transação (e o estado das agências é em memória, então ela volta "vazia", como registrado nas limitações). Mitigações possíveis: líder **estável** (só troca se a atual cair, como no Raft), log de transações persistido para a nova líder recuperar, e números de mandato (*term*) para rejeitar mensagens da líder antiga.

**3. E se a rede estiver só lenta (> 1 s), sem a agência estar fora do ar?**

Na eleição, uma resposta que passa de 1 s é tratada como "não respondeu": a agência menor concluiria que nenhuma maior está viva e se declararia líder, anunciando `coordenador` a todas, **com a maior viva**. Em geral isso se corrige sozinho, porque a requisição de eleição normalmente chegou e a maior (`receber_eleicao`) já agendou a própria eleição, vence e anuncia: sobra uma janela curta com duas líderes percebidas (*split brain* transitório). No heartbeat, um timeout isolado não derruba a líder (exijo 2 falhas). Se a rede fosse **persistentemente** lenta, a líder viva seria considerada morta e entraríamos em reeleições repetidas. Seria preciso timeout adaptativo ou mais falhas toleradas.

*Complemento (partição de rede).* O Bully assume que quem não responde está **caído**, não isolado: numa partição, cada lado elege o maior ID do seu lado (duas líderes) e, quando a rede volta, todas convergem para a maior viva. Resolver isso de verdade exige quórum (Raft/Paxos).

## Parte C - Perguntas (Seção 7.3)

**Quantas vezes a liderança mudou de mãos na "tempestade" inicial? Isso tem custo?**

No teste real (`eleicao-inicial.txt`) a liderança **não mudou de mãos**: houve 3 eleições iniciadas (uma por agência, em ~7 ms entre a primeira e a última) e um único mandato, o da agência 2, reconhecido pelas três em ~60 ms. O histórico reconstruído tem uma linha. Mesmo assim há custo, só que pequeno aqui: pelo código são pelo menos 3 mensagens de eleição (a 0 pergunta a 1 e 2, a 1 pergunta a 2) mais 2 de coordenador, além das eleições que cada agência maior dispara ao receber e dos eventos gravados nos 3 logs (não medi o total exato). Quando há trocas de verdade (agências subindo em tempos diferentes), cada troca custa uma nova rodada de coordenador (`n-1` mensagens), registros duplicados nos logs, oscilação do painel no app e, no Sprint 4, transações abortadas. Com 3 agências é desprezível; cresce com O(n²).

*Complemento (logs contra estado central).* Um estado central seria um ponto único de falha, justamente o que a eleição existe para evitar. Cada agência registra o que viu (`ELEICAO_INICIADA`, `NOVO_LIDER`, `LIDER_CAIU`) e o histórico é uma visão derivada, como o `mesclar_logs.py`. A mesma troca aparece até 3 vezes (uma por agência), então o script agrupa por líder e guarda quais agências a reconheceram. A ordem entre agências vem da hora de parede (só leitura humana); os vetores gravados permitem confirmar relações causais, mas, como no Sprint 2, **não dão ordem total**.

## Parte D - Perguntas (Seção 8.3)

**1. Com que frequência o app consulta `/bully/lider` e que trade-off foi considerado?**

O app consulta a cada **2 s** (`LiderancaService`, 3 `GET` em paralelo), e o timer é cancelado ao descartar o serviço (`parar()`/`dispose()`). Mais curto dá resposta mais rápida a trocas, mas acorda o rádio de dados com mais frequência (bateria) e gasta mais rede; mais longo poupa bateria, mas deixa o painel desatualizado justamente quando a líder cai. Como a liderança é só informativa neste sprint, 2 s (somados aos 2 a 4 s de detecção do backend) mostra o failover em poucos segundos sem custo relevante. Em produção eu usaria *push* (WebSocket ou FCM) em vez de polling, e pausaria o timer com o app em segundo plano. Não implementei pausa por ciclo de vida.

**2. Duas agências respondendo líderes diferentes na transição: como o app se comporta? É problema real?**

O app consulta as 3 e `_consenso()` conta os votos entre as agências vivas que conhecem uma líder: prevalece a mais citada. Se a líder escolhida está fora do ar, o app **não a exibe**: mostra "Eleição em andamento" (`liderAtual == null`). Num empate (1 contra 1) o desempate é arbitrário naquele ciclo. Não é um problema real: a janela dura de milissegundos a alguns segundos, o Bully converge e a próxima leitura (2 s depois) já concorda. E como nenhuma operação depende da líder neste sprint, o pior efeito é um painel errado por um ciclo. Se dependesse (Sprint 4), o app não deveria decidir pela líder: quem coordena é o backend.

**3. Arquitetura do app Flutter contra a do frontend web: o que foi reaproveitado e o que mudou?**

*Reaproveitado (conceitos):* o contrato REST com JWT (login, token no `Authorization: Bearer`, mesmos endpoints e erros 400/401/404/409); a separação em camadas (no web, `frontend/app.js` separa o Model, que fala com a API e guarda o token no `localStorage`, da View; no app: `ApiClient` para a API, `ContaRepositorio`/`LiderancaService` para o estado e as `*_page` para a UI); o tratamento visível de erros da API. *Pensado de forma diferente:* (1) **conectividade intermitente é regra no mobile**, o que levou ao offline-first (cache local, fila, UI otimista, sincronização ao reconectar), enquanto no web uma falha de rede só mostra erro; (2) **ciclo de vida e bateria** (polling, rede em segundo plano); (3) **armazenamento assíncrono** (`shared_preferences` atrás de uma interface, em vez do `localStorage` síncrono); (4) o "localhost" do celular/emulador não é o do PC, então os endereços das agências precisam ser **configuráveis** (`config.dart`); (5) estado reativo (`ChangeNotifier`) e testes de widget sem navegador.

*Complemento.* Consultar as 3 agências (e não só uma) evita que o painel fique cego quando justamente a agência consultada cai. Para operações da conta, a agência é fixa (`id % 3`): se ela cair, depósito e saque continuam offline (Parte F) e a transferência fica indisponível com aviso.

## Parte E - Perguntas (Seção 9.6)

**1. Por que comparar o vetor e não só o saldo?**

Saldo igual **não** significa estado igual: um depósito de 50 seguido de um saque de 50 por outro canal deixa o saldo idêntico, mas a conta mudou, e a operação feita offline foi pensada sobre um estado que já não existe. O vetor é uma **versão** que avança a cada evento, independentemente dos valores, então detecta qualquer mudança. Além disso distingue **ANTES** (o servidor evoluiu sem o app saber) de **CONCORRENTES** (ambos mudaram sem se conhecer), enquanto o saldo só diz "igual/diferente". E vale para qualquer tipo de operação (inclusive transferências) sem regras específicas. Os dois casos aparecem em `sincronizacao-409.txt`. Com Lamport (Sprint 1) dois timestamps diferentes só ordenam, não dizem se há relação causal.

**2. A simplificação de tratar qualquer mudança da agência como conflito**

No roteiro, o vetor é **por agência**: uma operação em *qualquer* conta avança o vetor e causaria conflito em todas as outras (falso positivo). No meu código isso já está refinado: cada conta guarda `versao`, o vetor da agência no instante da **última alteração daquela conta**, e o app envia como `vetorBase` a versão da conta que ele viu. Assim, uma operação em outra conta não gera conflito. Ainda é uma simplificação: o relógio continua sendo por agência (3 posições), e não por conta ou por dispositivo, e dois depósitos independentes na mesma conta (que poderiam ser combinados sem problema) ainda contam como conflito. Para ser mais preciso seria preciso operações comutativas (CRDTs) ou vetores por dispositivo.

**3. O que o app faz com um 409?** Ver a resposta 2 da Parte F: não descarta nem reaplica sozinho; mostra o estado real e pergunta à pessoa.

*Complemento.* A operação em conflito **não é aplicada nem descartada** pelo servidor: ele devolve o estado atual (HTTP 409) e quem decide é o usuário. Só `IGUAIS` ou `DEPOIS` são seguros para aplicar. A sincronização é idempotente por `idOperacao`.

## Parte F - Perguntas (Seção 10.3)

**1. Qual biblioteca de armazenamento local e por quê?**

`shared_preferences` (chave-valor em arquivo). O estado a guardar é pequeno (uma conta e uma fila curta de pendentes), e isso evita o plugin nativo do `sqflite`, que complicaria os testes. Alternativas consideradas: **`sqflite`** (SQL, bom para muitos registros e consultas, mais cerimônia), **Hive** (NoSQL leve e rápido, mas exige adaptadores e `init`) e **Drift** (camada tipada sobre SQLite, com geração de código). A persistência está atrás de uma interface (`ArmazenamentoLocal`), então trocar por SQLite não mexe no resto.

**2. O que aconteceu na tela quando a sincronização foi recusada (409)?**

A operação não some nem é aplicada: seu cartão ganha o selo **"Conflito"** (cor de erro), mostra a mensagem do servidor e **"No servidor agora: saldo X (versão ...)"**, e sai do saldo provisório. Aparecem dois botões: **"Descartar minha operação"** e **"Reenviar sobre o estado atual"**. Escolhi perguntar à pessoa porque descartar sozinho perderia a intenção do usuário, e reaplicar sozinho poderia somar sobre um saldo que ele nunca viu. O caso real, com o reenvio, está em `flutter-offline-first.txt`. Operações recusadas por outro motivo (por exemplo, saldo insuficiente) ficam como **"Rejeitada"**, também visíveis, com botão para remover.

**3. Que risco a UI otimista traz a um app bancário, e como o design o reduz?**

O risco é a pessoa ver um saldo provisório maior e decidir com base em dinheiro que o servidor pode recusar ("dinheiro fantasma"), por exemplo gastar o que ainda é só uma intenção. Para reduzir: o saldo exibido é *servidor + pendentes* e vem rotulado ("Inclui N operações ainda não confirmadas pelo servidor"); cada operação tem selo **Pendente**; conflitos e rejeitadas **saem** do saldo provisório mas continuam visíveis até serem resolvidos; a **transferência não funciona offline** (mexe em duas contas); o `idOperacao` evita aplicar duas vezes; e o servidor continua sendo a fonte da verdade, validando o saldo ao sincronizar (saque sem saldo recebe 400). Limite assumido: um saque offline ainda é otimista em relação ao saldo.

*Complemento (consistência eventual).* Sem rede, esperar a confirmação travaria o app. Durante a janela offline o app e o servidor divergem e convergem quando a fila sincroniza; o preço é que a divergência pode terminar em conflito, que precisa de uma política (aqui, decisão do usuário), como em Kleppmann (cap. 5).

## Funcionalidade adicional - Sprint 3 (Seção 2.1)

**Escolhida:** extrato por conta (`GET /contas/{id}/extrato`, JWT) e aba **Extrato** no app.

**Por que essa:** não há tabela de transações; a fonte de verdade é o log de eventos de cada agência. O extrato é uma **visão derivada desse log**, o que mostra que o log guarda o necessário para reconstruir o histórico de uma conta. Inclui abertura, depósito, saque, transferências enviadas e recebidas (local e entre agências) e operações sincronizadas do app; conflitos ficam de fora porque nunca foram aplicados.

**Evidência:** `evidencias/sprint3/funcionalidade-adicional.txt` (a soma dos movimentos confere com o saldo). Commits próprios: `86acada` (backend) e `4013775` (app).

## Desvios em relação ao roteiro

Decisões deliberadas, que mantêm o objetivo do roteiro:

- **Linguagem:** backend em Python/FastAPI (seção 11 do roteiro), não Node. As rotas `POST /bully/eleicao`, `POST /bully/coordenador` e `GET /bully/lider` seguem o formato pedido.
- **Nomes de eventos:** `ELEICAO_INICIADA`, `NOVO_LIDER` (cobre `TORNOU_LIDER` e `LIDER_ANUNCIADO`) e `LIDER_CAIU` (equivale a `LIDER_NAO_RESPONDEU`). `ELEICAO_RECEBIDA` não é registrada.
- **Heartbeat:** exige 2 falhas seguidas antes de reeleger (o roteiro reelege na primeira), para evitar falso positivo.
- **Sincronização:** `POST /sincronizar` (não `/contas/:id/sincronizar`), com `idOperacao` idempotente, **versão por conta** (não o vetor da agência inteira) e aplicação também quando a base é `DEPOIS`; qualquer outro caso é 409. É mais preciso que o roteiro e responde à pergunta 9.6.2.
- **Offline só para depósito e saque** (o roteiro deixa a transferência opcional).
- **Pasta do app:** `mobile/` (o roteiro cita `app_mobile/`).
- **Histórico de lideranças:** `historico_lideranca.py` (Python) e a tabela de mandatos em vez de uma lista de eventos.

## Evidências

Os 8 prints do roteiro (seção 4.2) estão em `evidencias/sprint3/`, capturados de uma **execução real** em 12/11/2026: as 3 agências em consoles do Windows (com `Get-Date` visível) e o app Flutter num emulador Android (Pixel 6, Android 35) apontando para as agências reais (`10.0.2.2`). Os registros `.txt` anteriores continuam na pasta como complemento.

| Print pedido pelo roteiro | O que mostra | Complemento em texto |
|---|---|---|
| `eleicao-inicial.png` | As 3 agências sobem e `/bully/lider` devolve a mesma líder (2) nas três | `eleicao-inicial.txt` |
| `failover.png` | Líder (agência 2) derrubada às 23:03:01; às 23:03:11 as outras duas concordam na líder 1 | `failover-heartbeat.txt` |
| `historico-lideranca.png` | Tabela de mandatos reconstruída dos logs (2, 1, 2, 1, 2) | `historico-lideranca.txt` |
| `app-lider-atual.png` | Painel do app: líder atual, as 3 agências no ar e o histórico de mudanças | `flutter-painel-lider.txt` |
| `app-failover.png` | Mesma tela antes, durante ("Eleição em andamento") e depois (nova líder), sem tocar no app | `flutter-painel-lider.txt` |
| `conflito-sincronizacao.png` | `POST /sincronizar` com vetor antigo devolve 409 `ANTES`; com o vetor atual devolve 200 | `sincronizacao-409.txt` |
| `app-offline.png` | Modo avião, depósito feito offline aparece como **Pendente** (saldo provisório) sem erro | `flutter-offline-first.txt` |
| `app-sincronizacao.png` | Ao reconectar, o app sincroniza sozinho e a operação deixa de ser pendente | `flutter-offline-first.txt` |

Extras: `app-conflito-409.png` (tarefa 5 da seção 10.2: o app mostra o 409 de forma visível, com o estado real da conta e os botões para decidir) e `funcionalidade-adicional.png` (aba Extrato). `app-failover.png` e `app-sincronizacao.png` são montagens lado a lado de capturas tiradas em sequência, sem editar o conteúdo delas.

## Limitações conhecidas

- Estado em memória (Sprint 1): reiniciar uma agência perde as contas, o que afeta a sincronização e a mensageria.
- Split brain numa partição de rede (Parte B).
- Rotas de Bully sem autenticação entre serviços (Parte A).
- Transferência não funciona offline (Parte F).
- A aba Extrato do app carrega ao ser criada e não se atualiza sozinha: se for aberta antes de a conta existir, mostra "Conta não encontrada" até tocar em "Tentar de novo" (observado durante os prints).

---

# RESPOSTAS - Sprint 4 (ICEIBank)

## Declaração de uso de IA

A declaração dos sprints anteriores continua valendo: o **Claude Code** (Anthropic) implementou a maior parte deste sprint (backend, testes, Dockerfile, compose, Lambdas e este arquivo) sob minha direção e revisão. Sou responsável por entender e defender qualquer trecho entregue.

O código de exemplo do roteiro é Node/Express; como o backend é **Python/FastAPI**, o protocolo foi **portado**, não copiado (seção 11 do roteiro). Os testes automatizados e os cenários de falha rodaram contra o código Python.

## O que foi e o que não foi executado de verdade

| Parte | Estado |
|---|---|
| Persistência, 2PC, Bully com token, `transacoes.py` | Implementados em Python e testados: 156 testes `pytest` e `agencia/cenarios_falha.py` (3 agências **reais**, em 3 processos, com quedas injetadas) |
| Imagens Docker, `docker compose up`, volumes, `restart: on-failure`, healthcheck | **Escritos, mas não executados**: o Docker Desktop não estava em execução na máquina de desenvolvimento. O `restart: on-failure` foi imitado por um supervisor dentro de `cenarios_falha.py` |
| LocalStack (SNS, SQS, Lambda, S3, DynamoDB, API Gateway), `init.sh` | **Não executados** (exigem o token do LocalStack e o Docker). O código das duas Lambdas e da publicação no SNS foi testado com clientes falsos (`tests/test_nuvem.py`); `init.sh` e os `awslocal apigateway ...` nunca rodaram |
| Prints de `evidencias/sprint4/` | **Pendentes**: dependem de Docker e LocalStack. Não foram fabricados |

## Decisões de design e desvios em relação ao roteiro

- **Python em vez de Node.** Estado em `src/services/armazenamento.py` (`EstadoDuravel`), com `threading.RLock`: o FastAPI atende cada requisição em uma thread, então `preparar`, `decidir` e `salvar()` precisam de exclusão mútua (o aviso da seção 11).
- **`estado.json` único por agência** com contas, operações de sincronização e estados do 2PC, gravado por `tmp` + `fsync` + `os.replace`. O log de eventos (`.jsonl`) continua separado, no mesmo `DATA_DIR`.
- **Saque recusado continua HTTP 400** (o roteiro cita 422). Mantive 400 para não quebrar o frontend e o app Flutter, que já tratam esse código. A transferência abortada devolve **422**, como o roteiro pede, com `detail` (o frontend e o app já leem `detail`) e `mensagem` no 200.
- **`GET /contas/{id}`** passou a devolver também `reservado` e `disponivel`; a criação de conta não mudou (os testes antigos continuam valendo).
- **Extrato (Sprint 3):** o extrato deriva do log de eventos, então ensinei-o a ler `2PC_COMMIT_APLICADO`; sem isso, transferências feitas pelo 2PC sumiriam do extrato (regressão silenciosa).
- **Mensageria (Sprint 2):** o consumidor do RabbitMQ continua no código, mas só sobe se `RABBITMQ_URL` estiver definida (no compose não há RabbitMQ). A transferência **não usa mais** a fila: usa o 2PC.
- **Token interno** em `/bully/eleicao`, `/bully/coordenador` e `/2pc/*`; sem `TOKEN_INTERNO` configurado, essas rotas recusam tudo (falha fechada). `GET /bully/lider` e `GET /saude` ficam públicos.
- **Bully:** `receber_coordenador` rejeita líder de id menor que o da própria agência e dispara eleição (seção 6.4).
- **Funcionalidade adicional (seção 2.1):** (1) **timeouts configuráveis** por variável de ambiente (`TIMEOUT_2PC`, `INTERVALO_REENTREGA`, `INTERVALO_RESOLUCAO`; o compose as repassa) e (2) **`GET /saude`** público, usado no `healthcheck` do compose. Foram usadas nos cenários de falha (reentrega de 1 s ou 60 s conforme o cenário).
- **Lambdas em Python** (a linguagem do backend): `serverless/gerar-comprovante` e `serverless/consultar-comprovante` (`GET /comprovantes/{txId}` via API Gateway). O DynamoDB não aceita `float`: o valor é convertido para `Decimal` (sem isso, toda mensagem iria para `batchItemFailures` para sempre).
- **Comprovantes só com SNS ativo** (`SNS_TOPIC_ARN`); publicação em thread própria, timeout de 2 s, sem retentativas e sem levantar exceção para o coordenador.

## Parte A - Perguntas (Seção 5.10)

**1. Por que gravar em um temporário e renomear?** Uma escrita direta no arquivo definitivo é um truncar-e-reescrever: se a agência cai no meio, sobra um JSON cortado (ou vazio) e a agência perde **todo** o estado, inclusive promessas de votos SIM. Com `tmp` + `fsync` + `os.replace`, o arquivo definitivo é sempre ou o estado antigo inteiro ou o novo inteiro (o rename é atômico); o `fsync` garante que o conteúdo do temporário já está no disco antes da troca.

**2. Sem o volume?** `docker compose down` + `up` recria os containers e o disco efêmero some: as contas desaparecem (voltamos ao problema do Sprint 2). No meio de um 2PC, um participante que perdeu o disco esquece as **promessas** (reservas e votos SIM). O coordenador pode ter decidido COMMIT contando com um SIM que ninguém lembra: o participante responderia "transação desconhecida" ao COMMIT (aqui, HTTP 409) e o débito/crédito jamais seria aplicado, quebrando a atomicidade. Por isso o estado fica em volume.

**3. O vetor não persistido viola a causalidade?** Sim, nos logs. Cenário: a agência 0 registra um evento com vetor `[5,0,0]`, envia uma mensagem à agência 1 (que passa a `[5,1,0]`), reinicia e o vetor volta a `[0,0,0]`; o próximo evento da 0 é `[1,0,0]`, que o `mesclar_logs.py` julgará **anterior** ao `[5,0,0]` e **concorrente/anterior** ao evento da agência 1, embora tenha acontecido depois. (Nos logs dos cenários de falha se vê isso: após cada queda os vetores recomeçam.) Correção simples: persistir o vetor junto com o estado (a cada `ao_enviar`/`evento_local`) ou, ao subir, reconstruí-lo pelo máximo do que está no log de eventos.

**4. Limites do token interno.** É um segredo estático e compartilhado: quem o descobrir (log, variável de ambiente, cópia do `.env`) passa a ser qualquer agência e pode chamar `/2pc/decidir`; não há identidade por agência, nem expiração, nem rotação, e o tráfego é HTTP sem criptografia (o token trafega em claro). Mais robusto: TLS mútuo (cada agência com seu certificado), rede privada/overlay onde só as agências se enxergam (as portas 4000-4002 não precisariam estar expostas ao host), e tokens por agência com escopo e expiração.

## Parte B - Perguntas (Seção 6.6)

**1. Por que gravar a promessa antes de responder SIM?** O SIM é um compromisso: "eu consigo aplicar quando você mandar". Se a resposta saísse antes da gravação e a agência caísse entre as duas coisas, o coordenador teria um SIM que o participante não lembra: ao reiniciar, ele não tem reserva nem registro, e pode aceitar outro débito do mesmo dinheiro ou responder "desconhecida" ao COMMIT. Gravando antes, no pior caso o participante lembra de uma promessa que o coordenador nunca recebeu (cenário 2), e isso se resolve consultando o coordenador.

**2. Idempotência.** Aplicar a mesma mensagem duas vezes produz o mesmo estado que aplicá-la uma. A rede pode duplicar (retransmissão após timeout) ou o coordenador pode reenviar a decisão porque não recebeu a confirmação; sem idempotência, um COMMIT repetido debitaria duas vezes. Aqui é garantida pela chave `txId:tipo` e pelo estado (`PREPARADO` → `COMMITADO`/`ABORTADO`); só se aplica a partir de `PREPARADO`.

**3. Por que não abortar sozinho por timeout?** Porque o coordenador pode já ter decidido COMMIT (e outro participante pode já ter aplicado). Se este abortasse por conta própria, haveria um débito sem crédito, ou o contrário. Só o coordenador sabe a decisão; o participante em dúvida tem de perguntar (`GET /2pc/status/{txId}`), e esse é o custo do 2PC (o bloqueio).

**4. Por que reservar na fase 1?** Para que o SIM seja verdadeiro até a decisão. Sem a reserva, duas transferências simultâneas de 60 de uma conta com 100 votariam SIM, e na fase 2 a segunda deixaria o saldo negativo. Com a reserva, a segunda vê `disponivel = 40` e vota NAO (coberto por `test_duas_transferencias_simultaneas_nao_gastam_o_mesmo_dinheiro`).

## Parte C - Perguntas (Seção 7.4)

**1. Decisão em disco antes de comunicar.** Se o coordenador comunicasse primeiro e caísse antes de gravar, um participante poderia ter aplicado COMMIT enquanto o coordenador, ao voltar, não tem decisão e aplica o aborto presumido: inconsistência. Gravando antes, quem voltar sabe o que foi decidido (cenário 4: o COMMIT sobrevive à queda).

**2. Por que o aborto presumido é seguro (e COMMIT presumido não).** Se a transação ainda estava na fase 1, nenhuma decisão foi tomada, logo ninguém recebeu COMMIT nem aplicou nada: abortar apenas libera reservas. Presumir COMMIT seria afirmar algo que talvez nem todos tenham prometido (um participante pode ter votado NAO ou nem ter respondido) e aplicaria um débito sem poder garantir o crédito.

**3. Coordenador e participante ao mesmo tempo.** Não é problema: as chamadas são as mesmas rotas HTTP, mesmo para si (a líder chama o próprio `/2pc/preparar`), e a chave `txId:tipo` separa o débito do crédito quando as duas contas estão na mesma agência. Os travamentos não ocorrem porque `preparar`/`decidir` seguram o `RLock` só durante a operação em memória + gravação, nunca durante uma chamada de rede. Coberto em `test_transferencia_mesma_agencia_participa_duas_vezes`.

**4. Sprint 2 x 2PC.** No Sprint 2 o débito era aplicado e só depois se publicava a mensagem: uma queda ou conta inexistente entre as duas etapas fazia o dinheiro sumir. O 2PC garante **atomicidade**: ou as duas operações se aplicam, ou nenhuma (inclusive conta de destino inexistente: o crédito vota NAO e o débito nem é aplicado). O custo: mais mensagens e **latência** (duas voltas de rede mais gravações em disco por transferência) e **disponibilidade** menor: qualquer agência fora do ar aborta a transferência, e a queda do coordenador deixa reservas presas (cenário 5).

## Parte D - Cenários de falha (Seção 8)

Executados com `python agencia/cenarios_falha.py` (3 agências reais, uma por processo, estado em disco, supervisor imitando `restart: on-failure`). Em cada cenário o script verifica o invariante: soma dos saldos igual a 3000 e nenhuma reserva presa. O resultado completo está em `evidencias/sprint4/cenarios-falha.txt`.

Execução final: **todas as verificações passaram** (`RESULTADO: TODOS OS CENARIOS OK`). Nos cenários 2 e 3 a reentrega do coordenador foi ajustada para 60 s, de modo que o **único** caminho para sair da dúvida fosse o participante consultar o coordenador (nos demais ela é de 1 s). As saídas abaixo vêm dos logs das agências.

| Cenário | O que fiz | Esperado | Observado | Invariante |
|---|---|---|---|---|
| Base | Transferência 0→1 de 100 pelo cliente falando com a agência 0 (a líder é a 2) | COMMIT nas duas agências | `200 COMMIT`; saldos 900/1100; a líder registrou `2PC_PREPARAR_ENVIADO`, `2PC_DECISAO_COMMIT`, `2PC_DECISAO_ENVIADA`, `2PC_CONCLUIDA` | soma 3000, reservas 0 |
| Abort | Saldo insuficiente (99999) e destino inexistente (conta 99) | ABORT sem efeito | `422` "Saldo insuficiente."; com destino 99 o **débito não foi aplicado** (no Sprint 2 era o caso em que o dinheiro sumia) | soma 3000, reservas 0 |
| 1. Participante fora do ar | `stop` da agência 1 e transferência 0→1 | ABORT por timeout | `422`; log `2PC_VOTO_TIMEOUT` na líder (`{'agencia': 1}`) | soma 3000, reservas 0 |
| 2. Cai depois de votar | `FALHA_2PC=participante-apos-votar` na agência 1; transferência 1→0 (débito na agência que cai) | Líder conta NAO e decide ABORT; a agência 1 volta em dúvida e consulta | `[FALHA INJETADA] participante-apos-votar: derrubando a agencia 1 agora`; na líder `2PC_VOTO_TIMEOUT`; o supervisor reiniciou a agência (`quedas=1`) e ela registrou `2PC_RESOLVIDA_POR_CONSULTA ... 'decisao': 'ABORT'` | soma 3000, reservas 0 |
| 3. Coordenador cai antes de decidir | `FALHA_2PC=coordenador-antes-de-decidir` na líder (agência 2); transferência 0→1 | Participantes com a reserva presa; a líder volta e aborta | cliente recebeu `503`; `[FALHA INJETADA] coordenador-antes-de-decidir`; ao voltar a líder registrou `2PC_ABORTO_PRESUMIDO`; os participantes consultaram e receberam ABORT | soma 3000, reservas 0 |
| 4. Coordenador cai depois de decidir COMMIT | `FALHA_2PC=coordenador-apos-decidir` na líder; transferência 0→1 | A decisão sobrevive e é entregue | cliente recebeu `503`, mas os saldos foram de 900/1100 para **800/1200**: a transferência se completou depois | soma 3000, reservas 0 |
| 5. Bloqueio | Como o 3, mas com `stop` da agência 2 assim que cai (ela não volta) | Participantes bloqueados | `2PC_BLOQUEADA_AGUARDANDO_COORDENADOR {'coordenador': 2}` na agência 0; `GET /contas/0` com `saldo 800, reservado 100, disponivel 700`; o participante continua `PREPARADO` depois de várias tentativas; um saque que incluía o valor reservado foi recusado. Ao subir a agência 2: aborto presumido e `2PC_RESOLVIDA_POR_CONSULTA ... ABORT`, reserva liberada | soma 3000, reservas 0 |

Observações honestas:

- **Cenário 4 expõe um problema real de API:** a mensagem de 503 dizia "Nada foi aplicado; tente novamente", o que seria falso (e perigoso: repetir duplicaria a transferência). Foi o que a execução mostrou; corrigi o texto para "o resultado será resolvido sozinho: confira os saldos antes de tentar de novo". A solução de verdade está na pergunta 3 abaixo.
- **Corrida inofensiva na base:** em uma das execuções, um participante registrou `2PC_RESOLVIDA_POR_CONSULTA` para a transação base (`97344da0`), na mesma hora em que o coordenador entregava a decisão (provável corrida entre a consulta periódica e a entrega). Como `decidir` é idempotente, o efeito foi aplicado uma vez só.
- **Saque recusado vem como HTTP 400**, não 422 (decisão registrada acima).
- Os saldos em cada cenário são cumulativos (o script não zera o estado entre cenários, só confere o invariante).
- O cenário do Docker (`docker compose stop agencia-1` etc.) **não foi executado**: o script reproduz os mesmos pontos de falha com processos reais; refazer com o Docker e tirar os prints é o que falta.

### Perguntas (Seção 8.7)

**1. Cenário 2: por que a promessa em disco não gera inconsistência?** Porque a decisão é do coordenador, não do participante. O coordenador não recebeu o voto (a agência caiu antes de responder), contou como NAO e decidiu ABORT; o SIM gravado no participante é só uma promessa pendente, que "vence" quem decide: o coordenador. Ao voltar, o participante vê a promessa em `PREPARADO`, pergunta `GET /2pc/status/{txId}` ao coordenador, recebe `ABORT` e libera a reserva (log `2PC_RESOLVIDA_POR_CONSULTA`).

**2. Cenário 5: safety ou liveness?** É falha de **liveness** (progresso/disponibilidade). Nada de errado é feito (a segurança é preservada: ninguém aplica metade da transferência, a soma dos saldos não muda e o dinheiro reservado não pode ser gasto), mas o sistema **não progride** enquanto o coordenador está fora: os participantes ficam bloqueados, com o dinheiro preso, sem poder decidir sozinhos. O 2PC escolhe segurança em vez de disponibilidade.

**3. Cenário 4: o cliente recebeu erro, mas a transferência aconteceu. É aceitável?** Para um banco não é aceitável como está, porque a reação natural do cliente (tentar de novo) duplicaria a transferência. Observei exatamente isso: o 503 chega, e instantes depois o COMMIT é entregue. Mitigação mínima feita: a mensagem de 503 agora diz que o resultado será resolvido sozinho e para conferir o saldo. O correto: a API aceitar um **`idempotencyKey`/`txId` gerado pelo cliente** (a repetição do mesmo pedido devolve o resultado da primeira, em vez de criar outra transferência) e expor a **consulta do resultado por `txId`** (o comprovante da Parte F faz isso, mas só depois de a nuvem processá-lo; o `GET /2pc/status/{txId}` é interno).

**4. A líder cai e o Bully elege outra: quem resolve as transações em andamento?** O código não cobre. A recuperação (aborto presumido, reentrega) é executada pelo **mesmo** processo da coordenadora quando ela **volta** (`recuperar()` e `reentregar_pendentes()` olham o estado dela, em disco). Quem assume a liderança não tem esse estado (ele está no volume da líder antiga) e, se perguntado sobre o `txId`, responderia ABORT por desconhecimento (aborto presumido), **mesmo que a antiga já tivesse decidido COMMIT**: um risco real de inconsistência. Os participantes em dúvida continuam perguntando à coordenadora original (`p["coordenador"]`), então ficam bloqueados até ela voltar. Faltaria: replicar o log de decisões do coordenador (Paxos/Raft, ou ao menos um log compartilhado) e permitir que a nova líder assuma e conclua as transações pendentes.

## Parte E - Observabilidade (Seção 9)

`python agencia/transacoes.py` (com `TOKEN_INTERNO` no ambiente) consulta `/2pc/transacoes` das 3 agências. Depois de uma transferência bem-sucedida: a líder mostra `[coordenador] ... estado=CONCLUIDA decisao=COMMIT`, e as duas agências das contas mostram `[participante] ... estado=COMMITADO` (um `DEBITO` e um `CREDITO`). No bloqueio (cenário 5): os participantes mostram `PREPARADO` (em dúvida), o coordenador aparece `fora do ar` e, quando volta, mostra a transação `DECIDIDA` com `decisao=ABORT` (aborto presumido), até a reentrega concluí-la.

### Perguntas (Seção 9.3)

**1. O estado só cresce: é problema? Que política de limpeza?** Num sistema real é: o arquivo de estado é reescrito inteiro a cada mudança, então o custo de cada gravação cresce com o histórico. Política: remover transações `CONCLUIDA` (coordenador) e `COMMITADO`/`ABORTADO` (participante) depois de uma janela de retenção, mantendo o histórico no log/arquivo morto. Cuidado com o aborto presumido: o coordenador **não pode esquecer** uma transação ainda não confirmada por todos (se esquecer e um participante ainda em dúvida perguntar, a resposta "desconhecida = ABORT" seria errada para um COMMIT que ele não aplicou). Só se apaga o que todos os participantes já confirmaram (`CONCLUIDA`).

**2. Onde o vetor ajuda mais que o horário de parede?** Quando os relógios físicos das agências divergem (ou apenas porque o log de uma agência registra o evento antes do da outra por milissegundos): o vetor mostra a ordem **causal** real. Por exemplo, em `2PC_DECISAO_ENVIADA` (líder) e `2PC_ABORT_APLICADO` (participante), o vetor do participante domina o da líder, provando que a aplicação foi consequência do envio, e dois eventos com vetores incomparáveis (ex.: dois participantes votando ao mesmo tempo) são de fato concorrentes. O horário não distingue "aconteceu depois por causa de" de "aconteceu depois por coincidência". Limite observado: como o vetor não é persistido, o recomeço após uma queda reinicia a contagem (Parte A, pergunta 3).

## Parte F - Perguntas (Seção 10.7)

(Código testado só com clientes falsos; LocalStack e AWS real não foram executados; veja a tabela do início.)

**1. Idempotência da Lambda.** Em `serverless/gerar-comprovante/lambda_function.py`, o `put_item` usa `ConditionExpression="attribute_not_exists(txId)"` e ignora `ConditionalCheckFailedException`; o `put_object` no S3 sobrescreve a mesma chave `comprovantes/{txId}.json`, então regravar não duplica nada. Cenário: o SQS entrega a mensagem, a Lambda processa e grava, mas cai (ou excede o tempo) antes de o SQS receber a confirmação de exclusão; passado o *visibility timeout* a mensagem é entregue de novo. Coberto por `test_gerar_comprovante_e_idempotente_na_reentrega`.

**2. Por que `batchItemFailures`.** Se a função lançasse uma exceção, o SQS consideraria **o lote inteiro** com falha e reentregaria todas as mensagens, inclusive as já processadas (reprocessamento desnecessário e, para sorte nossa, inofensivo graças à idempotência). Com `batchItemFailures`, só os `messageId` listados voltam à fila. Coberto por `test_so_a_mensagem_que_falha_volta_para_a_fila`.

**3. Cair entre decidir e publicar.** Não é aceitável para um sistema que promete comprovante de toda transferência. Padrão **outbox**: no mesmo `salvar()` atômico que grava a decisão, gravar também o evento a publicar em uma lista `outbox` do estado; uma tarefa periódica (como a `reentregar_pendentes`) publica o que está no outbox e só apaga o item depois de o SNS confirmar. Na recuperação, o que sobrou no outbox é publicado de novo (entrega "pelo menos uma vez", e a Lambda já é idempotente). Não implementado neste sprint.

**4. Containers x serverless.** Containers (coordenação): mantêm estado e conexões, latência previsível, bom para o 2PC (que precisa de disco, de reentrega periódica e de processo longo), porém custam enquanto estão ligados e escalam manualmente. Serverless (comprovante): escala sozinho e a custo por invocação, ótimo para trabalho curto, sem estado e disparado por evento; em contrapartida tem partida a frio, tempo máximo de execução e nenhum disco/estado local confiável. O 2PC seria má ideia numa função: o coordenador precisa gravar a decisão de forma durável, sobreviver a quedas e continuar reentregando por tempo indeterminado, e uma função efêmera (que pode ser encerrada a qualquer momento e é invocada de forma duplicada) não oferece nada disso.

**5. Onde a AWS real difere.** Permissões (IAM): o LocalStack aceita qualquer papel/credencial; na AWS real, sem permissão de `s3:PutObject`, `dynamodb:PutItem` e `sqs:*` para o papel da função, tudo falharia com `AccessDenied`. Limites e latência: partida a frio da Lambda, limites de concorrência/payload, SNS/SQS com atraso real e reentregas mais frequentes; o API Gateway real exige *stage*/URLs diferentes. Custos: cobrança por requisição, armazenamento e tráfego, inexistentes localmente.
