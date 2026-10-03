# Como capturar as evidências da Sprint 2

Todo o código já foi implementado, testado (unitário + integração real
contra um broker RabbitMQ) e mergeado na `main`. Os comandos abaixo foram
validados de ponta a ponta durante o desenvolvimento - é só copiar e colar,
igual ao guia da Sprint 1 (`evidencias/sprint1/COMO-CAPTURAR-EVIDENCIAS.md`).

## 0. Suba o RabbitMQ e defina `RABBITMQ_URL`

Se for usar CloudAMQP (recomendado para a entrega final - veja seção
"RabbitMQ (Sprint 2)" no README principal), copie a AMQP URL da sua
instância. Se preferir rodar local via Docker:

```powershell
docker run -d --name rabbitmq-iceibank -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

Em **todo terminal** onde for rodar uma agência ou o `auditoria.py`, defina:

```powershell
$env:RABBITMQ_URL="amqp://guest:guest@localhost:5672/"   # ou a URL do CloudAMQP
```

Suba as 3 agências (3 janelas, com `cd agencia`, venv ativado e
`RABBITMQ_URL` definida em cada uma):

```powershell
$env:AGENCIA_ID=0; python -m uvicorn src.app:app --port 4000
$env:AGENCIA_ID=1; python -m uvicorn src.app:app --port 4001
$env:AGENCIA_ID=2; python -m uvicorn src.app:app --port 4002
```

No 4º terminal (também com `RABBITMQ_URL` definida), faça login:

```powershell
Get-Date
$login = Invoke-RestMethod -Uri "http://localhost:4000/auth/login" -Method Post -ContentType "application/json" -Body '{"usuario":"aluno","senha":"senha123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
```

## 1. `transferencia-assincrona.png`

```powershell
Invoke-RestMethod -Uri "http://localhost:4000/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":0,"nomeAluno":"Ana","saldoInicial":100}'
Invoke-RestMethod -Uri "http://localhost:4001/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":1,"nomeAluno":"Bia","saldoInicial":0}'
Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":1,"valor":30}'
Start-Sleep -Seconds 1
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers
Invoke-RestMethod -Uri "http://localhost:4001/contas/1" -Headers $headers
```

Capture este terminal **e** as janelas das agências 0 e 1 (mostram
`[Vetor ...] TRANSFERENCIA_DEBITO` / `TRANSFERENCIA_CREDITO_REMOTO` no
console).

## 2. `resiliencia-fila.png`

Derrube a janela da **Agência 1** (Ctrl+C), depois:

```powershell
Get-Date
Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":1,"valor":20}'
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers   # debito aplicado mesmo com destino fora do ar
```

Suba a Agência 1 de novo (mesmo comando de antes). Depois de alguns
segundos:

```powershell
Get-Date
try { Invoke-RestMethod -Uri "http://localhost:4001/contas/1" -Headers $headers }
catch { Write-Host "HTTP" $_.Exception.Response.StatusCode.value__ "-" $_.ErrorDetails.Message }
```

Capture a sequência inteira (derrubar → transferir → subir → conta não
encontrada), incluindo o console da Agência 1 mostrando
`CREDITO_REMOTO_FALHOU`.

## 3. `linha-do-tempo-causal.png`

Com as 3 agências no ar, crie uma conta em cada uma **ao mesmo tempo** (em
3 terminais diferentes, ou colando os 3 comandos bem rápido em sequência):

```powershell
Get-Date
Invoke-RestMethod -Uri "http://localhost:4002/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":2,"nomeAluno":"Caio","saldoInicial":0}'
```

Depois:

```powershell
cd agencia
python mesclar_logs.py
```

Capture a saída inteira - a seção "Pares de eventos CONCORRENTES" deve
mostrar pelo menos os `CRIAR_CONTA` das 3 agências entre si.

## 4. `funcionalidade-adicional.png` (fila de auditoria)

Abra um **5º terminal** (com `RABBITMQ_URL` definida) e rode:

```powershell
cd agencia
python auditoria.py
```

Deixe rodando. No 4º terminal, faça mais uma transferência entre agências:

```powershell
Get-Date
Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":1,"valor":10}'
```

Capture o terminal da auditoria mostrando `[AUDITORIA] credito capturado:
...` - ou, se a saída não aparecer na hora (buffer), rode:

```powershell
Get-Content agencia\data\auditoria.jsonl
```

---

Depois de capturar os 4 prints, adicione e feche o sprint:

```powershell
git add evidencias/sprint2
git commit -m "docs(evidencias): adiciona prints da Sprint 2"
git push
```
