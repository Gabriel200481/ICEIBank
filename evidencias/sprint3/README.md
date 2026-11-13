# Evidências - Sprint 3

## Prints (seção 4.2 do roteiro)

Capturas de uma **execução real** em 12/11/2026: as 3 agências em consoles do Windows (com `Get-Date` visível) e o app Flutter em um emulador Android (Pixel 6, Android 35), apontando para as agências reais.

| Print | O que mostra | Parte |
|---|---|---|
| `eleicao-inicial.png` | As 3 agências sobem e `/bully/lider` devolve a mesma líder nas três | A |
| `failover.png` | Líder derrubada e reeleição automática; consulta às agências restantes | B |
| `historico-lideranca.png` | Saída do `historico_lideranca.py` com a linha do tempo de mandatos | C |
| `app-lider-atual.png` | App Flutter mostrando a líder atual | D |
| `app-failover.png` | Painel do app antes, durante e depois da queda da líder, sem ação do usuário | D |
| `conflito-sincronizacao.png` | Backend recusando a sincronização desatualizada (409) e aceitando com o vetor atual | E |
| `app-offline.png` | App em modo avião com a operação feita offline aparecendo como pendente | F |
| `app-sincronizacao.png` | App reconectando e sincronizando sozinho a operação pendente | F |
| `app-conflito-409.png` | *(extra)* o app tratando o 409 de forma visível, com o estado real da conta | F |
| `funcionalidade-adicional.png` | *(extra)* aba Extrato do app | Extra |

`app-failover.png` e `app-sincronizacao.png` são montagens lado a lado de capturas tiradas em sequência, sem edição do conteúdo.

## Registros em texto (complemento)

Saídas reais de terminal e de testes, com data/hora e o comando no topo de cada arquivo.

| Arquivo | O que prova | Parte |
|---|---|---|
| `eleicao-inicial.txt` | 3 agências sobem quase juntas e convergem para a mesma líder (agência 2) apesar da tempestade de eleições | A |
| `failover-heartbeat.txt` | Líder derrubada, reeleição automática (agência 1), líder original volta e retoma a liderança | B |
| `historico-lideranca.txt` | Linha do tempo de mandatos reconstruída dos logs reais do failover | C |
| `flutter-fluxo-bancario.txt` | Mesmo `ApiClient` do app: login, conta, depósito, saque, transferência, extrato e painel acompanhando a queda real da líder | D |
| `flutter-painel-lider.txt` | Saída do `flutter test`, incluindo o teste do failover visível no painel | D |
| `sincronizacao-409.txt` | `POST /sincronizar`: caminho feliz, idempotência, conflito `ANTES` e `CONCORRENTES` (HTTP 409), conta intacta | E |
| `flutter-offline-first.txt` | Modo avião, fila, UI otimista, sincronização ao reconectar, 409 real e reenvio sobre o estado atual | F |
| `funcionalidade-adicional.txt` | Extrato por conta; a soma confere com o saldo e a operação em conflito não aparece | Extra |

Reproduzir: ver os comandos no topo de cada arquivo e o README da raiz.
