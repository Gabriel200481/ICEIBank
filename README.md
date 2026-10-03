# ICEIBank

> Banco simplificado dividido em agências, desenvolvido ao longo de 4 sprints para aplicar, na prática, os principais conceitos de Sistemas Distribuídos (relógio de Lamport, relógio vetorial, consenso e transações distribuídas) sobre uma API REST/MVC real.

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

| Sprint | Unidade da ementa       | Tecnologia         | Conceito de Sistemas Distribuídos | Status         |
| ------ | ------------------------ | ------------------- | ----------------------------------- | -------------- |
| 1      | U2 - Desenvolvimento Web | API REST / MVC       | Relógio lógico de Lamport         | Concluída |
| 2      | U3 - Comunicação indireta | Mensageria / Pub-Sub | Relógio vetorial                   | Código completo — [evidências de terminal pendentes](evidencias/sprint2/COMO-CAPTURAR-EVIDENCIAS.md) |
| 3      | U4 - Desenvolvimento Móvel | App Flutter          | Consenso (eleição de líder)        | Não iniciada |
| 4      | U5 - Computação em Nuvem | Containers            | Transações distribuídas (2PC/Saga) | Não iniciada |

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
- [ ] `evidencias/sprint2/` completa — guia em [evidencias/sprint2/COMO-CAPTURAR-EVIDENCIAS.md](evidencias/sprint2/COMO-CAPTURAR-EVIDENCIAS.md)

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

---

## Funcionalidades Principais

- **Particionamento de contas:** cada agência só opera contas sob sua responsabilidade (`id_conta % 3`).
- **CRUD de contas + depósito/saque:** cada operação carimbada com relógio vetorial.
- **Transferência local:** entre contas da mesma agência.
- **Transferência entre agências (Sprint 2):** publish/subscribe via RabbitMQ - a origem publica, a agência de destino consome de forma assíncrona (entrega sobrevive à queda temporária do destino).
- **Relógio vetorial:** substitui o relógio de Lamport do Sprint 1 - permite provar com certeza se dois eventos são causalmente relacionados ou concorrentes.
- **Limitação conhecida (proposital):** as contas vivem em memória; se a agência de destino reiniciar antes de consumir uma mensagem pendente, o crédito não encontra a conta (registrado como `CREDITO_REMOTO_FALHOU`, nunca aplicado silenciosamente - ver teste de resiliência em RESPOSTAS.md).
- **Linha do tempo causal:** script que mescla os `.jsonl` das três agências e aponta pares de eventos comprovadamente concorrentes, comparando vetores.
- **Fila de auditoria:** consumidor extra com routing key coringa (`agencia.*.creditar`) que escuta todo crédito de qualquer agência, independente do processamento normal.
- **Autenticação JWT:** login com expiração de token, protegendo todas as rotas de contas.
- **Frontend web:** login, saldo, depósito, saque e transferência, consumindo a API autenticada.
- **Funcionalidade adicional:** ver [RESPOSTAS.md](RESPOSTAS.md).

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
| Pytest      | 8.3     | Testes unitários e de integração                  |

### Infraestrutura

| Tecnologia | Uso                                                              |
| ----------- | ------------------------------------------------------------------ |
| RabbitMQ    | Message broker (exchange topic, filas por agência - Sprint 2). CloudAMQP (gerenciado) ou Docker local. |

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
│   ├── src/
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── controllers/
│   │   │   ├── contas_controller.py
│   │   │   ├── transferencias_controller.py
│   │   │   ├── auth_controller.py
│   │   │   └── status_controller.py
│   │   └── services/
│   │       ├── vector_clock.py      (Sprint 2 - substitui lamport_clock.py)
│   │       ├── mensageria.py        (Sprint 2 - publish/subscribe via RabbitMQ)
│   │       ├── event_log.py
│   │       └── auth_service.py
│   ├── tests/                      (testes automatizados - pytest)
│   ├── data/                       (logs gerados em tempo de execução - não versionado)
│   ├── mesclar_logs.py
│   └── auditoria.py                 (Sprint 2 - funcionalidade adicional)
├── frontend/                       (HTML/CSS/JS puro)
├── evidencias/
│   ├── sprint1/
│   └── sprint2/
├── RESPOSTAS.md
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

---

## Testes

Cada peça é testada isoladamente (unitário) antes de ser integrada à API, e a integração é validada com as 3 agências rodando de verdade (requisições HTTP reais via `curl`/`Invoke-RestMethod`, e o frontend dirigido por um navegador real). **57 testes automatizados** (pytest) na Sprint 2 - a maioria roda sem precisar de infraestrutura externa (RabbitMQ é simulado via monkeypatch nos testes de controller); um pequeno grupo (`test_mensageria.py`, `test_auditoria.py`) valida publish/subscribe de ponta a ponta contra um broker real, pulado automaticamente se `RABBITMQ_URL` não estiver definida.

```powershell
cd agencia
.venv\Scripts\Activate.ps1
pytest -v

# para rodar tambem os testes de integracao com RabbitMQ real:
$env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"; pytest -v
```

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
