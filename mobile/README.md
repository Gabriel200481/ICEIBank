# ICEIBank Mobile (Flutter)

App do Sprint 3: fluxo bancário (login, saldo, depósito, saque, transferência), painel de liderança (Bully) com failover visível e, na Parte F, modo offline-first.

Consome a API das agências **sem alterar contratos** (REST + JWT do Sprint 1). Conta N é atendida pela agência `N % 3`.

## Rodar

1. Suba as 3 agências (ver README da raiz; portas 4000-4002).
2. `flutter pub get`
3. `flutter run -d chrome` (web) ou, no emulador Android, `flutter run --dart-define=AGENCIA_HOST=10.0.2.2`
4. Login: usuário `aluno`, senha `senha123` (usuário de demonstração do backend).

## Testes

```
flutter analyze
flutter test
```

`dart run tool/painel_cli.dart 30` usa o mesmo `ApiClient` do app contra agências reais e imprime o que o painel de liderança mostraria (derrube a líder durante a execução para ver o failover).

## Estrutura

| Arquivo | Papel |
|---|---|
| `lib/api_client.dart` | Chamadas HTTP com timeout; erros viram `ApiException` / `SemConexaoException` |
| `lib/lideranca_service.dart` | Polling das 3 agências; consenso da líder; histórico de mudanças |
| `lib/lideranca_page.dart` | Painel de liderança (atualiza sozinho) |
| `lib/conta_page.dart` | Saldo, depósito, saque, transferência, fila de pendentes e tratamento de conflito |
| `lib/conta_repositorio.dart` | Offline-first: cache local, fila de pendentes, UI otimista, sincronização |
| `lib/operacao_pendente.dart` | Operação na fila (`pendente` / `conflito` / `rejeitada`) |
| `lib/armazenamento.dart` | Armazenamento local (SharedPreferences; versão em memória nos testes) |
| `lib/conectividade.dart` | Detecção de rede (`connectivity_plus`) |

## Modo offline-first

- Depósito e saque entram numa **fila local** e o saldo muda na hora (UI otimista); a fila sobrevive a fechar o app.
- Ao reconectar (ou a cada 5 s enquanto houver pendentes) o app envia a fila em ordem para `POST /sincronizar`, cada operação com o `vetorBase` (versão da conta que o app conhecia).
- **HTTP 409** (conflito detectado pelo relógio vetorial) nunca é escondido: a operação fica marcada como *Conflito*, com o estado atual do servidor, e o usuário escolhe *Descartar* ou *Reenviar sobre o estado atual*.
- Transferência entre contas **não** é enfileirada (exige conexão): ela mexe em duas contas, possivelmente de agências diferentes, e o roteiro do sincronismo cobre só uma conta por operação.
- Teste contra agência real: `ICEIBANK_REAL=1 flutter test test/integracao_real_test.dart` (agência 0 no ar na porta 4000).
