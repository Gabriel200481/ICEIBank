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
- **Evidências:** o roteiro pede prints `.png`; o que existe hoje são saídas reais de terminal e de testes em `evidencias/sprint3/` (ver a seção "Evidências" abaixo). As capturas do app dependem de emulador e estão pendentes (issue #68).

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

O roteiro pede 8 prints `.png` (seção 4.2). O que existe hoje são saídas reais de terminal e de testes em `evidencias/sprint3/` (`.txt`, com data e comando). Mapa:

| Print pedido pelo roteiro | Registro atual |
|---|---|
| `eleicao-inicial.png` | `eleicao-inicial.txt` |
| `failover.png` | `failover-heartbeat.txt` |
| `historico-lideranca.png` | `historico-lideranca.txt` |
| `conflito-sincronizacao.png` | `sincronizacao-409.txt` |
| `app-lider-atual.png` | `flutter-painel-lider.txt` (testes) e `flutter-fluxo-bancario.txt` |
| `app-failover.png` | `flutter-painel-lider.txt` (teste do failover) |
| `app-offline.png` e `app-sincronizacao.png` | `flutter-offline-first.txt` |

**Pendente:** as capturas de tela `.png`, principalmente as do app, dependem de rodar o app em um emulador; acompanhadas na issue #68.

## Limitações conhecidas

- Estado em memória (Sprint 1): reiniciar uma agência perde as contas, o que afeta a sincronização e a mensageria.
- Split brain numa partição de rede (Parte B).
- Rotas de Bully sem autenticação entre serviços (Parte A).
- Transferência não funciona offline (Parte F).
- A regressão não reexecutou o RabbitMQ real nem o frontend web em navegador real; ver README.
- Prints `.png` do app ainda não capturados (issue #68).
