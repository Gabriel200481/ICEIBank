---

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
![JWT](https://img.shields.io/badge/Auth-JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-testado-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

| Sprint | Unidade da ementa       | Tecnologia         | Conceito de Sistemas Distribuídos | Status         |
| ------ | ------------------------ | ------------------- | ----------------------------------- | -------------- |
| 1      | U2 - Desenvolvimento Web | API REST / MVC       | Relógio lógico de Lamport         | Em andamento |
| 2      | U3 - Comunicação indireta | Mensageria / Pub-Sub | Relógio vetorial                   | Não iniciada |
| 3      | U4 - Desenvolvimento Móvel | App Flutter          | Consenso (eleição de líder)        | Não iniciada |
| 4      | U5 - Computação em Nuvem | Containers            | Transações distribuídas (2PC/Saga) | Não iniciada |

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

O ICEIBank é um banco fictício particionado em agências independentes: cada conta pertence a exatamente uma agência (`id_conta % numero_de_agencias`), sem replicação. Neste sprint, três agências rodam simultaneamente (mesmo código-fonte, identidades diferentes via variável de ambiente), cada uma com sua própria API REST/MVC para criar contas, consultar saldo, depositar, sacar e transferir - local ou entre agências.

Toda operação é registrada com um timestamp de relógio lógico de Lamport, e um script auxiliar (`mesclar_logs.py`) mescla os logs das três agências em uma linha do tempo única, permitindo observar o algoritmo de Lamport funcionando de verdade sobre operações concorrentes.

Este sprint também exige autenticação via JWT protegendo a API e um frontend web que a consome.

---

## Funcionalidades Principais

- **Particionamento de contas:** cada agência só opera contas sob sua responsabilidade (`id_conta % 3`).
- **CRUD de contas + depósito/saque:** cada operação carimbada com relógio lógico de Lamport.
- **Transferência local:** entre contas da mesma agência.
- **Transferência entre agências:** chamada REST direta agência-a-agência, usando as regras `ao_enviar()`/`ao_receber()` do relógio de Lamport.
- **Falha conhecida (proposital):** se a agência de destino cair no meio de uma transferência entre agências, o débito não é revertido - a inconsistência é registrada no log (será resolvida no Sprint 4, com 2PC/Saga).
- **Linha do tempo unificada:** script que mescla os `.jsonl` das três agências, ordenados por relógio de Lamport.
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
| httpx       | 0.27    | Chamadas REST entre agências (transferência remota) |
| Pytest      | 8.3     | Testes unitários e de integração                  |

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
        ├─ Services (RelogioLamport, RegistroEventos, JWT)
        │
Estado em memória (contas: dict, por processo/agência)
        │
Log de eventos (agencia/data/eventos-agencia-N.jsonl)
```

Comunicação entre agências (transferência remota):

```
Agência de origem                         Agência de destino
  debita localmente
  relogio.ao_enviar() ──► POST /contas/{id}/creditar-remoto ──► relogio.ao_receber(ts)
                                                                  credita localmente
```

---

## Instalação e Execução

### Pré-requisitos

- Python 3.11+ (testado com 3.13)
- pip

### Variáveis de ambiente (opcionais - têm valor padrão de desenvolvimento)

```env
JWT_SECRET=troque-por-um-segredo-forte-em-producao
JWT_EXPIRACAO_MINUTOS=15
AGENCIA_SERVICE_TOKEN=segredo-compartilhado-entre-agencias
OFFSET=0
```

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
│   │   │   └── auth_controller.py
│   │   └── services/
│   │       ├── lamport_clock.py
│   │       ├── event_log.py
│   │       └── auth_service.py
│   ├── tests/                      (testes automatizados - pytest)
│   ├── data/                       (logs gerados em tempo de execução - não versionado)
│   └── mesclar_logs.py
├── frontend/                       (HTML/CSS/JS puro)
├── evidencias/
│   └── sprint1/
├── RESPOSTAS.md
├── .gitignore
└── README.md
```

---

## Demonstração

Fluxo validado de ponta a ponta (backend real + frontend real, ver
[evidencias/sprint1/](evidencias/sprint1/)):

1. Login em `/auth/login` (tela de login do frontend)
2. Criar conta 0 na Agência 0 e conta 1 na Agência 1 (trocando o seletor de agência)
3. Consultar saldo, depositar
4. Tentar sacar mais do que o saldo disponível → erro tratado, mensagem visível na tela
5. Transferir da conta 0 (agência 0) para a conta 1 (agência 1) → transferência entre agências, confirmada nos saldos das duas agências
6. `python mesclar_logs.py` → linha do tempo unificada das 3 agências, ordenada por relógio de Lamport

---

## Testes

Cada peça é testada isoladamente (unitário) antes de ser integrada à API, e a integração é validada com as 3 agências rodando de verdade (requisições HTTP reais via `curl`/`Invoke-RestMethod`).

```powershell
cd agencia
.venv\Scripts\Activate.ps1
pytest -v
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
- LAMPORT, Leslie. *Time, Clocks, and the Ordering of Events in a Distributed System*. Communications of the ACM, v. 21, n. 7, 1978.

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
