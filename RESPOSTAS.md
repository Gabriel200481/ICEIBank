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
