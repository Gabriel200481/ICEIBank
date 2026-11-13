# Evidências - Sprint 3

As 8 evidências são **saídas reais de terminal e de testes**, geradas rodando as 3 agências e o app (não são capturas de tela de interface gráfica; o app Flutter foi exercitado por `flutter test` e por um cliente real contra as agências, sem emulador). Cada arquivo traz data/hora e o comando.

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
