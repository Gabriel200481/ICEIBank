# ICEIBank

> Banco simplificado dividido em agências, desenvolvido ao longo de 4 sprints para aplicar, na prática, os principais conceitos de Sistemas Distribuídos (relógio de Lamport, relógio vetorial, consenso, transações distribuídas e nuvem serverless) sobre uma API REST/MVC real.

🎥 **[Vídeo de apresentação (Sprints 1 a 4)](evidencias/apresentacao-sprints-1-2-3-4.mp4)** - código e funcionamento ao vivo de cada funcionalidade pedida nos 4 roteiros.

<table>
	<tr>
		<td width="800px">
			<div align="justify">
				Projeto individual da disciplina Laboratório de Desenvolvimento de Aplicações Móveis e Distribuídas. Cada agência do ICEIBank é um serviço REST independente (mesmo código, identidades diferentes), responsável por uma partição de contas. Toda operação é carimbada com um relógio lógico de Lamport, permitindo observar - de forma real e verificável - como um sistema distribuído ordena eventos sem depender de um relógio físico global.
			</div>
		</td>
	</tr>
</table>

---

## Status do Projeto

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-333333?style=for-the-badge&logo=gunicorn&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-Pub%2FSub-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white)
![JWT](https://img.shields.io/badge/Auth-JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-testado-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Flutter](https://img.shields.io/badge/Flutter-App%20mobile-02569B?style=for-the-badge&logo=flutter&logoColor=white)

| Sprint | Unidade da ementa       | Tecnologia         | Conceito de Sistemas Distribuídos | Status         |
| ------ | ------------------------ | ------------------- | ----------------------------------- | -------------- |
| 1      | U2 - Desenvolvimento Web | API REST / MVC       | Relógio lógico de Lamport         | Concluída |
| 2      | U3 - Comunicação indireta | Mensageria / Pub-Sub | Relógio vetorial                   | Concluída |
| 3      | U4 - Desenvolvimento Móvel | App Flutter          | Consenso (eleição de líder - Bully) | Concluída |
| 4      | U5 - Computação em Nuvem | Containers + LocalStack | Transações distribuídas (2PC) | Concluída |

**Sprint 1 - checklist de entrega** (seção 13 do roteiro):

- [x] Repositório com histórico de commits incremental (uma branch + PR por issue)
- [x] 3 agências rodando simultaneamente, particionamento respeitado
- [x] CRUD de contas + depósito/saque com timestamp de Lamport
- [x] Transferência local e entre agências
- [x] Falha conhecida reproduzida e documentada (não escondida)
- [x] `mesclar_logs.py` funcionando, testado com concorrência real
- [x] Autenticação JWT (login, expiração, proteção de rotas, 3 cenários testados)
- [x] Frontend funcional consumindo a API autenticada (testado em navegador real)
- [x] Funcionalidade adicional (`GET /status`) implementada e documentada
- [x] `RESPOSTAS.md` completo (todas as perguntas + justificativas de design)
- [x] `evidencias/sprint1/` completa (11 prints: frontend + terminal, todos reais)
- [x] [Vídeo de apresentação](evidencias/sprint1/apresentacao-sprint1.mp4)

**Sprint 2 - checklist de entrega** (seção 10 do roteiro):

- [x] RabbitMQ configurado (exchange topic `iceibank.eventos`, fila por agência, routing keys corretas)
- [x] Relógio vetorial substituindo o relógio de Lamport, 3 regras implementadas
- [x] Transferência entre agências via mensageria assíncrona (REST direto removido)
- [x] Teste de resiliência reproduzido e documentado (agência derrubada, mensagem retida, conta perdida ao reiniciar)
- [x] `mesclar_logs.py` identificando corretamente pares concorrentes
- [x] JWT e frontend do Sprint 1 continuam funcionando (regressão testada em navegador real)
- [x] Funcionalidade adicional (fila de auditoria com routing key coringa) implementada e documentada
- [x] `RESPOSTAS.md` atualizado (seções 6.4, 7.5, 8.3 + funcionalidade adicional)
- [x] Suite de testes automatizados rodando limpa (57 testes, incluindo integração real contra RabbitMQ)
- [x] `evidencias/sprint2/` completa (4 prints de terminal reais)

**Sprint 3 - checklist de entrega** (seção 12 do roteiro):

- [x] Mensagens de eleição e coordenador implementadas e funcionando (Parte A)
- [x] As 3 agências convergem para a mesma líder ao subir, mesmo com a "tempestade" de eleições inicial
- [x] Heartbeat detectando a queda da líder e disparando reeleição automática (Parte B), sem intervenção manual
- [x] Script `historico_lideranca.py` reconstruindo a linha do tempo de lideranças (Parte C)
- [x] App Flutter com o fluxo bancário completo, reaproveitando a API já existente
- [x] App Flutter com painel de liderança, atualizado automaticamente, incluindo o failover visível na tela
- [x] Endpoint de sincronização no backend (Parte E), detectando conflito via relógio vetorial (409), não só o caminho feliz
- [x] App Flutter em modo offline-first (Parte F): armazenamento local, fila de pendentes, UI otimista e sincronização automática ao reconectar
- [x] O conflito de sincronização (HTTP 409) é tratado de forma visível no app
- [x] JWT (testes automatizados), frontend web (não alterado; só usa `id`, `nomeAluno` e `saldo`, que não mudaram) e mensageria/relógio vetorial sem regressão (pytest com RabbitMQ real, transferência entre agências pelo broker e frontend em Chrome real; ver `evidencias/sprint3/regressao.txt`)
- [x] Funcionalidade adicional (extrato por conta, backend + app) implementada e documentada
- [x] `evidencias/sprint3/` com os 8 prints `.png` do roteiro (terminal e app em emulador), registros em texto e a regressão (ver o README da pasta)
- [x] `RESPOSTAS.md` atualizado (seções 5.5, 6.4, 7.3, 8.3, 9.6 e 10.3 + funcionalidade adicional)

---

**Sprint 4 - checklist de entrega** (seção 12 do roteiro):

- [x] Estado das agências persistido em disco com escrita atômica (Parte A)
- [x] 3 agências em containers, com volumes e reinício automático (`docker compose up` funcionando do zero)
- [x] Rotas internas protegidas por token (`x-token-interno`), com `GET /bully/lider` e `GET /saude` mantidos públicos
- [x] Participante do 2PC: reserva de fundos, voto durável, idempotência (Parte B)
- [x] Coordenador: decisão durável, reentrega e aborto presumido (Parte C)
- [x] Transferência entre agências usa o 2PC e não debita sem creditar (substitui a mensageria do Sprint 2)
- [x] Os 5 cenários de falha executados e documentados ao vivo (via Docker real), com o invariante (soma dos saldos, reservas) verificado em cada um (Parte D)
- [x] Bloqueio do 2PC provocado e observado de propósito (coordenador que não volta)
- [x] Script `transacoes.py` funcionando (Parte E)
- [x] LocalStack real no ar e `gerar-comprovante` produzindo comprovantes no S3 e no DynamoDB após cada transferência (Parte F)
- [x] Segunda função Lambda (`consultar-comprovante`) exposta por API Gateway
- [x] Transferência concluindo normalmente com o LocalStack parado (a nuvem não está no caminho crítico)
- [x] Segredos fora do repositório (`.env` no `.gitignore`)
- [x] JWT, frontend web, mensageria (Sprint 2), Bully e app Flutter (Sprint 3) continuam funcionando sem regressão (156 testes automatizados passando)
- [x] Funcionalidade adicional (timeouts do 2PC configuráveis por variável de ambiente + `GET /saude`) implementada e documentada
- [x] `evidencias/sprint4/` com os 13 prints da seção 4.2, capturados ao vivo
- [x] `RESPOSTAS.md` atualizado (seções 5.10, 6.6, 7.4, 8.7, 9.3, 10.7 + registros dos cenários + funcionalidade adicional)

**Sprint 4 - como rodar** (containers, 2PC e nuvem local):

```powershell
Copy-Item .env.example .env          # ajuste TOKEN_INTERNO (e LOCALSTACK_AUTH_TOKEN, para a Parte F)
docker compose up --build            # 3 agencias em containers, com volumes (estado em /dados)
$env:TOKEN_INTERNO = "troque-este-segredo"; python agencia/transacoes.py   # estado do 2PC em cada agencia

# Parte F (nuvem local): empacota as Lambdas, sobe o LocalStack e cria os recursos
New-Item -ItemType Directory -Force -Path serverless/build | Out-Null
Compress-Archive -Path serverless/gerar-comprovante/lambda_function.py -DestinationPath serverless/build/gerar-comprovante.zip -Force
Compress-Archive -Path serverless/consultar-comprovante/lambda_function.py -DestinationPath serverless/build/consultar-comprovante.zip -Force
docker compose --profile nuvem up --build -d
docker compose exec localstack sh /scripts/init.sh

# cenarios de falha da Parte D sem Docker (3 processos reais + supervisor que imita restart: on-failure)
python agencia/cenarios_falha.py
```

Transferências passam pelo **Two-Phase Commit**: a líder eleita pelo Bully coordena; as agências das duas contas participam (reserva de fundos no débito, voto e decisão gravados em disco). Rotas internas (`/bully/eleicao`, `/bully/coordenador`, `/2pc/*`) exigem o cabeçalho `x-token-interno`; `GET /bully/lider` e `GET /saude` continuam públicos. Detalhes, cenários de falha e respostas em [RESPOSTAS.md](RESPOSTAS.md).

---

## Índice

- [Links Úteis](#links-úteis)
- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades Principais](#funcionalidades-principais)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Arquitetura](#arquitetura)
- [Instalação e Execução](#instalação-e-execução)
- [Estrutura de Pastas](#estrutura-de-pastas)
- [Demonstração](#demonstração)
- [Testes](#testes)
- [Fluxo de trabalho (Issues, Branches e Project)](#fluxo-de-trabalho-issues-branches-e-project)
- [Documentações Utilizadas](#documentações-utilizadas)
- [Autores](#autores)

---

## Links Úteis

- **Board do projeto (Backlog/To Do/Doing/In Review/Done):** https://github.com/users/Gabriel200481/projects/3
- **Issues:** https://github.com/Gabriel200481/ICEIBank/issues
- **Roteiro do Sprint 1:** enunciado fornecido pela disciplina (não incluso no repositório)
- **Respostas às questões do roteiro:** [RESPOSTAS.md](RESPOSTAS.md)

---

## Sobre o Projeto

O ICEIBank é um banco fictício particionado em agências independentes: cada conta pertence a exatamente uma agência (`id_conta % numero_de_agencias`), sem replicação. Três agências rodam simultaneamente (mesmo código-fonte, identidades diferentes via variável de ambiente), cada uma com sua própria API REST/MVC para criar contas, consultar saldo, depositar, sacar e transferir - local ou entre agências.

Toda operação é registrada com um **relógio vetorial** (Sprint 2 - substitui o relógio de Lamport do Sprint 1, que só garantia uma direção da causalidade), e um script auxiliar (`mesclar_logs.py`) mescla os logs das três agências e identifica, com certeza matemática, quais pares de eventos são causalmente relacionados e quais são genuinamente concorrentes.

Transferências entre agências não usam mais chamada REST direta: a agência de origem publica um evento numa exchange do **RabbitMQ**, e a agência de destino consome quando puder - mesmo que esteja fora do ar no momento da publicação, a mensagem fica retida numa fila durável até ser processada.

O projeto também tem autenticação via JWT protegendo a API e um frontend web que a consome.

A partir do Sprint 3, as agências elegem uma líder entre si pelo **algoritmo de Bully**, e um app **Flutter** (offline-first, com fila de pendentes) passa a consumir a mesma API. No Sprint 4, a transferência entre agências deixa de usar mensageria simples e passa pelo **Two-Phase Commit** (2PC) coordenado pela líder, com estado persistido em disco, as 3 agências rodando em **containers Docker**, e cada transferência decidida gerando um comprovante assíncrono numa nuvem local (**LocalStack**: SNS → SQS → Lambda → S3/DynamoDB), consultável por uma segunda Lambda via API Gateway.

---

## Funcionalidades Principais

Cada funcionalidade pedida nos roteiros, com link direto para onde ela está implementada no código (arquivo e linhas exatas no GitHub).

### Sprint 1 - API REST/MVC, Lamport, JWT, frontend

| Funcionalidade | Onde está no código |
| --- | --- |
| Particionamento de contas (`id_conta % 3`) | [`config.py` - `agencia_responsavel`, `url_da_agencia`](agencia/src/config.py#L43-L48) |
| Relógio lógico de Lamport (substituído pelo vetorial no Sprint 2 - código histórico) | [`lamport_clock.py` no commit `444831d`](https://github.com/Gabriel200481/ICEIBank/blob/444831d727094ca72b7e7e797226c533741e628a/agencia/src/services/lamport_clock.py) |
| CRUD de contas + depósito/saque | [`contas_controller.py` - `criar_conta`, `consultar_saldo`, `depositar`, `sacar`](agencia/src/controllers/contas_controller.py#L23-L90) |
| Transferência local (mesma agência) | [`transferencias_controller.py` - `transferir`](agencia/src/controllers/transferencias_controller.py#L39-L61) |
| Transferência remota síncrona + falha conhecida (substituída por mensageria no Sprint 2, depois por 2PC no Sprint 4 - código histórico) | [`transferencias_controller.py` no commit `444831d`](https://github.com/Gabriel200481/ICEIBank/blob/444831d727094ca72b7e7e797226c533741e628a/agencia/src/controllers/transferencias_controller.py#L85-L109) |
| `mesclar_logs.py` (linha do tempo unificada) | [`mesclar_logs.py` - `carregar_eventos`, `imprimir_linha_do_tempo`](agencia/mesclar_logs.py#L16-L30) |
| Autenticação JWT (login, expiração, proteção de rotas) | [`auth_controller.py`](agencia/src/controllers/auth_controller.py#L16-L33) + [`auth_service.py` - `criar_token`, `decodificar_token`](agencia/src/services/auth_service.py#L18-L33) |
| Frontend web | [`frontend/index.html`](frontend/index.html) + [`frontend/app.js`](frontend/app.js) |
| Funcionalidade adicional: `GET /status` | [`status_controller.py`](agencia/src/controllers/status_controller.py#L12-L21) |

### Sprint 2 - Mensageria (RabbitMQ) e relógio vetorial

| Funcionalidade | Onde está no código |
| --- | --- |
| RabbitMQ (exchange topic, fila por agência) | [`mensageria.py` - `url_rabbitmq`, `publicar`, `assinar`](agencia/src/services/mensageria.py#L24-L58) |
| Relógio vetorial (3 regras) | [`vector_clock.py` - `RelogioVetorial`](agencia/src/services/vector_clock.py#L23-L46) |
| Comparação de vetores (causal x concorrente) | [`vector_clock.py` - `comparar_vetores`](agencia/src/services/vector_clock.py#L47-L58) |
| Transferência entre agências via publish/subscribe (substituída pelo 2PC no Sprint 4 - código histórico) | [`transferencias_controller.py` no commit `0abf51c`](https://github.com/Gabriel200481/ICEIBank/blob/0abf51c2af105aee2b5fe13e7192753a17e9cc5d/agencia/src/controllers/transferencias_controller.py#L38-L70) |
| Teste de resiliência (mensagem retida na fila) | registrado em `CREDITO_REMOTO_FALHOU`, [`app.py` - `_processar_credito_recebido`](agencia/src/app.py#L112-L147) |
| Linha do tempo causal / pares concorrentes | [`mesclar_logs.py` - `encontrar_pares_concorrentes`](agencia/mesclar_logs.py#L32-L55) |
| Funcionalidade adicional: fila de auditoria (routing key coringa) | [`auditoria.py`](agencia/auditoria.py#L38-L74) |

### Sprint 3 - Consenso (Bully) e app Flutter

| Funcionalidade | Onde está no código |
| --- | --- |
| Algoritmo de Bully (eleição e coordenador) | [`bully.py` - classe `Bully`](agencia/src/services/bully.py#L69-L180) |
| Heartbeat e failover automático | [`bully.py` - `verificar_lider`, `iniciar_heartbeat`](agencia/src/services/bully.py#L181-L227) |
| Rotas de eleição (`/bully/*`) | [`bully_controller.py`](agencia/src/controllers/bully_controller.py#L28-L40) |
| `historico_lideranca.py` (linha do tempo de mandatos) | [`historico_lideranca.py` - `construir_mandatos`](agencia/historico_lideranca.py#L22-L59) |
| App Flutter - fluxo bancário (login, saldo, depósito, saque, transferência) | [`conta_page.dart`](mobile/lib/conta_page.dart), [`login_page.dart`](mobile/lib/login_page.dart) |
| App Flutter - painel de liderança (polling periódico nas 3 agências) | [`lideranca_service.dart`](mobile/lib/lideranca_service.dart) |
| Sincronização offline-first no backend (conflito 409 via relógio vetorial) | [`sync_controller.py` - `sincronizar`](agencia/src/controllers/sync_controller.py#L30-L100) |
| App Flutter offline-first (fila de pendentes, UI otimista, conflito 409) | [`conta_repositorio.dart` - `depositar`, `sincronizar`, `descartar`, `reenviarSobreEstadoAtual`](mobile/lib/conta_repositorio.dart#L119-L246) |
| Funcionalidade adicional: extrato por conta | [`extrato.py`](agencia/src/services/extrato.py#L12-L50) + [`extrato_page.dart`](mobile/lib/extrato_page.dart) |

### Sprint 4 - Transações distribuídas (2PC) e nuvem serverless

| Funcionalidade | Onde está no código |
| --- | --- |
| Persistência atômica em disco | [`armazenamento.py` - `EstadoDuravel`](agencia/src/services/armazenamento.py#L24-L60) |
| Containers (3 agências + volumes + healthcheck) | [`docker-compose.yml`](docker-compose.yml) |
| Rotas internas protegidas por token | [`autenticacao_interna.py`](agencia/src/middlewares/autenticacao_interna.py#L8-L12) |
| 2PC - papel de participante (voto durável, reserva de fundos) | [`participante.py` - `preparar`, `decidir`](agencia/src/services/participante.py#L26-L99) |
| 2PC - papel de coordenador (as 2 fases, decisão durável) | [`coordenador.py` - `coordenar`](agencia/src/services/coordenador.py#L91-L133) |
| Reentrega da decisão e aborto presumido | [`coordenador.py` - `reentregar_pendentes`, `recuperar`](agencia/src/services/coordenador.py#L135-L162) |
| Rotas do protocolo (`/2pc/*`) | [`protocolo_controller.py`](agencia/src/controllers/protocolo_controller.py#L32-L57) |
| Injeção de falhas controlada (Parte D) | [`falhas.py` - `falhar`](agencia/src/services/falhas.py#L17-L27) |
| `transacoes.py` (observabilidade do 2PC) | [`transacoes.py` - `descrever`](agencia/transacoes.py#L16-L39) |
| Publicação de eventos no SNS (nuvem local) | [`eventos_nuvem.py` - `EventosNuvem`](agencia/src/services/eventos_nuvem.py#L32-L66) |
| Lambda `gerar-comprovante` (SQS → S3 + DynamoDB) | [`serverless/gerar-comprovante/lambda_function.py`](serverless/gerar-comprovante/lambda_function.py) |
| Lambda `consultar-comprovante` (API Gateway) | [`serverless/consultar-comprovante/lambda_function.py`](serverless/consultar-comprovante/lambda_function.py) |
| Funcionalidade adicional: timeouts do 2PC configuráveis + `GET /saude` | [`config.py`](agencia/src/config.py#L34-L37) + [`status_controller.py`](agencia/src/controllers/status_controller.py#L22-L23) |

> Três itens apontam para commits antigos porque o próprio código evoluiu sobre eles ao longo dos sprints (Lamport → vetorial; REST direto → mensageria → 2PC) - a versão histórica ainda é um código real, testado e executado antes de ser substituído (ver `RESPOSTAS.md` para a justificativa de cada substituição).

---

## Tecnologias Utilizadas

### Back-end (por agência)

| Tecnologia | Versão | Uso                                              |
| ----------- | ------- | -------------------------------------------------- |
| Python      | 3.13    | Linguagem                                          |
| FastAPI     | 0.115   | Framework web (REST/MVC via `APIRouter`)          |
| Uvicorn     | 0.30    | Servidor ASGI                                      |
| PyJWT       | 2.9     | Emissão e validação de tokens JWT                |
| httpx       | 0.27    | Testes de API (TestClient)                        |
| pika        | 1.3     | Cliente RabbitMQ (publish/subscribe - Sprint 2)   |
| boto3       | 1.35    | Cliente AWS (SNS, S3, DynamoDB - Sprint 4, Parte F) |
| Pytest      | 8.3     | Testes unitários e de integração                  |

### Infraestrutura

| Tecnologia | Uso                                                              |
| ----------- | ------------------------------------------------------------------ |
| RabbitMQ    | Message broker (exchange topic, filas por agência - Sprint 2). CloudAMQP (gerenciado) ou Docker local. |
| Docker / Docker Compose | Containers das 3 agências, com volumes e healthcheck (Sprint 4) |
| LocalStack  | Nuvem AWS local (SNS, SQS, S3, DynamoDB, Lambda, API Gateway - Sprint 4, Parte F) |

### Front-end

| Tecnologia            | Uso                                                     |
| ----------------------- | -------------------------------------------------------- |
| HTML/CSS/JavaScript puro | Interface web, sem framework/build step (ver Parte G) |

---

## Arquitetura

Cada agência segue arquitetura em camadas (MVC), isolada das demais - a "distribuição" do sistema é literal: três processos independentes, cada um ouvindo em uma porta, comunicando-se via REST quando uma transferência cruza a partição.

```
Frontend (HTML/CSS/JS)
        │  HTTP + JWT (Authorization: Bearer <token>)
        ▼
Controllers (APIRouter por contexto: contas, transferencias, auth)
        │
        ├─ Services (RelogioVetorial, RegistroEventos, Mensageria, JWT)
        │
Estado em memória (contas: dict, por processo/agência)
        │
Log de eventos (agencia/data/eventos-agencia-N.jsonl)
```

Comunicação entre agências (transferência remota - Sprint 2, via RabbitMQ):

```
Agência de origem                                    Agência de destino
  debita localmente
  relogio.ao_enviar()
  publicar("agencia.<id>.creditar", msg) ──► iceibank.eventos ──► fila-agencia-<id>
                                                                       │
                                                          (consumida quando possível,
                                                           mesmo que a agência esteja
                                                           fora do ar no momento do publish)
                                                                       │
                                                                       ▼
                                                        relogio.ao_receber(vetor) + credita
```

Até o Sprint 1, essa comunicação era uma chamada REST direta e síncrona
(`POST /contas/{id}/creditar-remoto`) - se a agência de destino estivesse
fora do ar, a chamada falhava na hora. Esse endpoint não existe mais.

---

## Instalação e Execução

### Pré-requisitos

- Python 3.11+ (testado com 3.13)
- pip

### Variáveis de ambiente (opcionais - têm valor padrão de desenvolvimento)

```env
JWT_SECRET=troque-por-um-segredo-forte-em-producao
JWT_EXPIRACAO_MINUTOS=15
OFFSET=0

# Sprint 2 - obrigatoria (nao ha valor padrao, a app nao sobe sem ela)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### RabbitMQ (Sprint 2)

Duas opções, mesma variável `RABBITMQ_URL`:

- **CloudAMQP (gerenciado, como o roteiro recomenda):** crie uma instância gratuita "Little Lemur" em [cloudamqp.com](https://www.cloudamqp.com/), copie o campo **AMQP URL** (formato `amqps://usuario:senha@host.cloudamqp.com/vhost`) e use como `RABBITMQ_URL`.
- **Docker local (alternativa, usada durante o desenvolvimento deste sprint):**
  ```powershell
  docker run -d --name rabbitmq-iceibank -p 5672:5672 -p 15672:15672 rabbitmq:3-management
  ```
  Painel de administração em `http://localhost:15672` (usuário/senha padrão: `guest`/`guest`). `RABBITMQ_URL=amqp://guest:guest@localhost:5672/`.

### Back-end - subindo as 3 agências

```powershell
cd agencia
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Terminal 1
$env:AGENCIA_ID=0; python -m uvicorn src.app:app --port 4000

# Terminal 2
$env:AGENCIA_ID=1; python -m uvicorn src.app:app --port 4001

# Terminal 3
$env:AGENCIA_ID=2; python -m uvicorn src.app:app --port 4002
```

### Front-end

```powershell
cd frontend
python -m http.server 5500
```

Acesse `http://localhost:5500`.

### Linha do tempo unificada

```powershell
cd agencia
python mesclar_logs.py
```

---

## Estrutura de Pastas

```text
iceibank/
├── agencia/
│   ├── requirements.txt
│   ├── Dockerfile                   (Sprint 4 - imagem da agência)
│   ├── src/
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── controllers/
│   │   │   ├── contas_controller.py
│   │   │   ├── transferencias_controller.py (Sprint 4 - transferência via 2PC)
│   │   │   ├── auth_controller.py
│   │   │   ├── status_controller.py
│   │   │   ├── bully_controller.py      (Sprint 3 - eleição)
│   │   │   ├── sync_controller.py       (Sprint 3 - sincronização offline-first)
│   │   │   └── protocolo_controller.py  (Sprint 4 - rotas do 2PC)
│   │   ├── middlewares/
│   │   │   └── autenticacao_interna.py  (Sprint 4 - protege rotas internas)
│   │   └── services/
│   │       ├── vector_clock.py      (Sprint 2 - substitui lamport_clock.py)
│   │       ├── mensageria.py        (Sprint 2 - publish/subscribe via RabbitMQ)
│   │       ├── bully.py             (Sprint 3 - eleição de líder + heartbeat)
│   │       ├── extrato.py           (Sprint 3 - funcionalidade adicional)
│   │       ├── armazenamento.py     (Sprint 4 - estado durável em disco)
│   │       ├── participante.py      (Sprint 4 - papel de participante do 2PC)
│   │       ├── coordenador.py       (Sprint 4 - papel de coordenador do 2PC)
│   │       ├── falhas.py            (Sprint 4 - injeção de falhas da Parte D)
│   │       ├── eventos_nuvem.py     (Sprint 4 - publicação no SNS)
│   │       ├── cliente_interno.py   (Sprint 4 - chamadas HTTP entre agências)
│   │       ├── saldo.py             (Sprint 4 - saldo disponível = saldo - reservado)
│   │       ├── event_log.py
│   │       └── auth_service.py
│   ├── tests/                      (testes automatizados - pytest)
│   ├── data/                       (logs e estado gerados em tempo de execução - não versionado)
│   ├── mesclar_logs.py
│   ├── historico_lideranca.py       (Sprint 3 - linha do tempo de lideranças)
│   ├── auditoria.py                 (Sprint 2 - funcionalidade adicional)
│   ├── transacoes.py                (Sprint 4 - observabilidade do 2PC)
│   └── cenarios_falha.py            (Sprint 4 - os 5 cenários de falha, automatizados)
├── serverless/                      (Sprint 4 - Lambdas da Parte F)
│   ├── gerar-comprovante/lambda_function.py
│   └── consultar-comprovante/lambda_function.py
├── localstack/init.sh               (Sprint 4 - cria os recursos AWS no LocalStack)
├── docker-compose.yml               (Sprint 4 - 3 agências + LocalStack)
├── frontend/                       (HTML/CSS/JS puro)
├── mobile/                         (Sprint 3 - app Flutter, ver mobile/README.md)
├── evidencias/
│   ├── sprint1/
│   ├── sprint2/
│   ├── sprint3/
│   ├── sprint4/
│   └── apresentacao-sprints-1-2-3-4.mp4
├── RESPOSTAS.md
├── .env.example
├── .gitignore
└── README.md
```

---

## Demonstração

### Sprint 1 (ver [evidencias/sprint1/](evidencias/sprint1/))

1. Login em `/auth/login` (tela de login do frontend)
2. Criar conta 0 na Agência 0 e conta 1 na Agência 1 (trocando o seletor de agência)
3. Consultar saldo, depositar
4. Tentar sacar mais do que o saldo disponível → erro tratado, mensagem visível na tela
5. Transferir da conta 0 (agência 0) para a conta 1 (agência 1) → transferência entre agências, confirmada nos saldos das duas agências
6. `python mesclar_logs.py` → linha do tempo unificada das 3 agências, ordenada por relógio de Lamport

### Sprint 2 (ver [evidencias/sprint2/](evidencias/sprint2/))

Fluxo validado de ponta a ponta com RabbitMQ real (Docker local):

1. Transferência entre agências → debita na hora, publica na exchange, resposta imediata ("entrega assíncrona")
2. Agência de destino consome a mensagem (~1s depois) e credita - confirmado pelo saldo e pelo log (`TRANSFERENCIA_CREDITO_REMOTO`)
3. Teste de resiliência: agência de destino derrubada, nova transferência → ainda 200 OK (mensagem retida na fila); ao reiniciar, a conta não existe mais (estado em memória) e o log registra `CREDITO_REMOTO_FALHOU`, sem aplicar nada silenciosamente
4. `python mesclar_logs.py` → 3 contas criadas em paralelo em agências diferentes aparecem corretamente como concorrentes entre si; o par débito/crédito de uma transferência real não aparece (relação causal)
5. `python auditoria.py` rodando em paralelo às agências → captura uma cópia de todo crédito publicado, de qualquer agência, via routing key coringa
6. JWT e frontend testados novamente em navegador real - sem regressão

### Sprint 3 (ver [evidencias/sprint3/](evidencias/sprint3/))

Fluxo validado de ponta a ponta com as 3 agências reais e o app Flutter:

1. Subir as 3 agências quase juntas → as três convergem para a **agência 2** (maior ID), mesmo com a tempestade de eleições
2. Derrubar a líder → em ~1-2 s uma agência detecta pelo heartbeat, elege a **agência 1** e avisa a outra; o painel do app mostra a troca sozinho
3. Subir a agência 2 de novo → ela retoma a liderança (maior ID vivo)
4. `python historico_lideranca.py` → mandatos: 2 (queda detectada) → 1 (substituída) → 2 (em curso)
5. App offline: depósito e saque entram na fila, o saldo muda na hora; ao reconectar a fila sincroniza sozinha
6. Alterar a conta por outro aparelho enquanto o app está offline → ao reconectar, `POST /sincronizar` responde **409** e o app mostra o conflito com o estado do servidor (Descartar / Reenviar sobre o estado atual)

Subir uma agência continua igual ao Sprint 2 (o `RABBITMQ_URL` segue obrigatório para o consumidor de mensagens); a eleição inicia sozinha ~1,5 s depois:

```powershell
$env:AGENCIA_ID=0; $env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"; python -m uvicorn src.app:app --port 4000
```

Variáveis novas (todas opcionais): `HEARTBEAT_INTERVALO` (s, padrão 2), `HEARTBEAT_FALHAS` (falhas seguidas até reeleger, padrão 2), `BULLY_ATRASO_INICIAL` (s, padrão 1.5), `BULLY_DESLIGADO=1` (desliga a eleição automática, usado nos testes).

Rotas novas: `POST /bully/eleicao`, `POST /bully/coordenador`, `GET /bully/lider` (entre agências, sem JWT), `POST /sincronizar` e `GET /contas/{id}/extrato` (com JWT). As contas passaram a expor o campo `versao` (vetor da última alteração).

App mobile: ver [mobile/README.md](mobile/README.md).

### Sprint 4 (ver [evidencias/sprint4/](evidencias/sprint4/))

Fluxo validado de ponta a ponta com Docker e LocalStack reais:

1. `docker compose up --build` → as 3 agências sobem em containers e ficam saudáveis (`compose-up.png`)
2. `docker compose restart agencia-0` → o saldo sobrevive ao reinício (estado em disco, não mais em memória) (`persistencia-volume.png`)
3. Chamar `/2pc/transacoes` sem o header `x-token-interno` → 401 (`token-interno-401.png`)
4. Transferência normal entre agências → **COMMIT** via 2PC, com as duas fases (`PREPARAR_ENVIADO`, `DECISAO_COMMIT`, `DECISAO_ENVIADA`, `CONCLUIDA`) nos logs da líder (`2pc-commit.png`)
5. Transferência com saldo insuficiente → **ABORT**, sem nenhum efeito residual (`2pc-abort.png`)
6. Os 3 cenários de falha, injetados de verdade via `FALHA_2PC` + Docker: participante cai após votar e o Docker reinicia sozinho (`falha-participante.png`); coordenador (líder) cai antes de decidir e assume aborto presumido ao voltar (`falha-coordenador.png`); coordenador cai e **não volta** → a reserva fica presa de propósito até ele voltar (`bloqueio.png`)
7. `python transacoes.py` → estado do 2PC (coordenações e participações) em cada agência (`transacoes.png`)
8. `docker compose --profile nuvem up` + `init.sh` → LocalStack real no ar, com SNS/SQS/S3/DynamoDB/Lambda/API Gateway disponíveis (`localstack-saude.png`)
9. Uma transferência real gera o comprovante no S3 e o índice no DynamoDB via Lambda (`comprovante-s3-dynamo.png`), consultável pela segunda Lambda via API Gateway, inclusive o 404 de um `txId` inexistente (`api-comprovante.png`)
10. `docker compose stop localstack` + transferência → conclui normalmente (a nuvem não trava o 2PC); ao religar o LocalStack, o comprovante daquela transferência nunca existe (sem *outbox* - ver `RESPOSTAS.md`) (`nuvem-fora-do-ar.png`)

Como rodar: ver a seção **Sprint 4 - como rodar**, mais acima neste README.

---

## Testes

Cada peça é testada isoladamente (unitário) antes de ser integrada à API, e a integração é validada com as 3 agências rodando de verdade - como containers Docker no Sprint 4 (requisições HTTP reais via `curl`/`Invoke-RestMethod`, e o frontend dirigido por um navegador real). **156 testes automatizados** (pytest; 153 rodam sem nenhuma infraestrutura externa) e **62 testes do app** (`flutter test`, Sprint 3) - um pequeno grupo (`test_mensageria.py`, `test_auditoria.py`, `test_nuvem.py`) valida publish/subscribe e a nuvem local de ponta a ponta contra um broker/LocalStack reais, pulado automaticamente se a infraestrutura não estiver no ar.

```powershell
cd agencia
.venv\Scripts\Activate.ps1
pytest -v

# para rodar tambem os testes de integracao com RabbitMQ real:
$env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"; pytest -v

# app Flutter
cd ..\mobile
flutter analyze
flutter test
```

**Regressão do Sprint 4 (26/11/2026):** com Docker e LocalStack reais, a suíte completa do backend passou (**156 passed**), os 5 cenários de falha da Parte D foram reproduzidos ao vivo via containers (não só pelo script automatizado), e JWT, frontend web, mensageria/relógio vetorial e Bully continuaram funcionando sem regressão. Evidências em `evidencias/sprint4/`.

---

## Fluxo de trabalho (Issues, Branches e Project)

Todo o trabalho é rastreado no [Project do repositório](https://github.com/users/Gabriel200481/projects/3), com colunas **Backlog → To Do → Doing → In Review → Done**. Para cada issue:

1. Card sai do Backlog e entra em **To Do**, depois **Doing**.
2. Uma branch dedicada é criada a partir da `main` (`issue-N-descricao`).
3. Implementação + testes na branch.
4. Push da branch, Pull Request aberto, card movido para **In Review**.
5. Revisão do diff e do resultado dos testes.
6. Merge na `main`, card movido para **Done**.

---

## Documentações Utilizadas

- FastAPI: https://fastapi.tiangolo.com/
- Uvicorn: https://www.uvicorn.org/
- PyJWT: https://pyjwt.readthedocs.io/
- Pytest: https://docs.pytest.org/
- RabbitMQ (tutoriais Publish/Subscribe): https://www.rabbitmq.com/tutorials
- CloudAMQP: https://www.cloudamqp.com/
- pika: https://pika.readthedocs.io/
- LAMPORT, Leslie. *Time, Clocks, and the Ordering of Events in a Distributed System*. Communications of the ACM, v. 21, n. 7, 1978.
- FIDGE, Colin J. *Timestamps in Message-Passing Systems That Preserve the Partial Ordering*. Australian Computer Science Communications, 1988.
- MATTERN, Friedemann. *Virtual Time and Global States of Distributed Systems*. Parallel and Distributed Algorithms, 1989.

---

## Autores

| Nome                          | GitHub                                             | E-mail                          |
| ------------------------------ | --------------------------------------------------- | -------------------------------- |
| Gabriel Afonso Infante Vieira | [Gabriel200481](https://github.com/Gabriel200481) | gabrielvieira200481@gmail.com |

---

## Agradecimentos

- Laboratório de Desenvolvimento de Aplicações Móveis e Distribuídas
- Prof. Cleiton Tavares Silva e Prof. Cristiano de Macedo Neto

---

## Licença

Este projeto é distribuído sob a Licença MIT.

---
