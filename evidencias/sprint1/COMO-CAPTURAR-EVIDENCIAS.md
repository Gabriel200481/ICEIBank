# Como capturar as evidências pendentes

Todo o código deste sprint já foi implementado, testado (unitário + integração
com servidores reais) e mergeado na `main`. As evidências de frontend já estão
salvas aqui (`frontend-login.png`, `frontend-transferencia.png`,
`frontend-erro.png` - capturadas com um navegador real controlado
automaticamente). As evidências abaixo dependem de uma janela de terminal
visível na sua máquina (com `Get-Date` aparecendo, para provar execução
recente) e por isso precisam ser capturadas por você - os comandos abaixo já
foram validados (produzem exatamente esses resultados).

Suba as 3 agências antes de começar (3 janelas do PowerShell):

```powershell
cd agencia
python -m venv .venv        # se ainda nao existir
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Terminal 1
$env:AGENCIA_ID=0; python -m uvicorn src.app:app --port 4000
# Terminal 2
$env:AGENCIA_ID=1; python -m uvicorn src.app:app --port 4001
# Terminal 3
$env:AGENCIA_ID=2; python -m uvicorn src.app:app --port 4002
```

Em um quarto terminal (as capturas abaixo são desse quarto terminal):

## 1. `transferencia-local.png`

```powershell
Get-Date
$login = Invoke-RestMethod -Uri "http://localhost:4000/auth/login" -Method Post -ContentType "application/json" -Body '{"usuario":"aluno","senha":"senha123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }

Invoke-RestMethod -Uri "http://localhost:4000/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":0,"nomeAluno":"Ana","saldoInicial":100}'
Invoke-RestMethod -Uri "http://localhost:4000/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":3,"nomeAluno":"Bia","saldoInicial":10}'
Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":3,"valor":30}'
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers
Invoke-RestMethod -Uri "http://localhost:4000/contas/3" -Headers $headers
```

## 2. `transferencia-entre-agencias.png`

Capture este terminal **e** as janelas das agências 0 e 1 (elas imprimem
`[Lamport N] TIPO {...}` no console a cada evento - é o log "das duas
agências envolvidas" que o roteiro pede).

```powershell
Get-Date
Invoke-RestMethod -Uri "http://localhost:4001/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":1,"nomeAluno":"Caio","saldoInicial":0}'
Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":1,"valor":20}'
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers
Invoke-RestMethod -Uri "http://localhost:4001/contas/1" -Headers $headers
```

## 3. `falha-conhecida.png`

Feche a janela/processo da **Agência 2** (Ctrl+C) antes de rodar isto:

```powershell
Get-Date
try {
  Invoke-RestMethod -Uri "http://localhost:4000/transferencias" -Method Post -ContentType "application/json" -Headers $headers -Body '{"idOrigem":0,"idDestino":2,"valor":10}'
} catch {
  Write-Host "HTTP" $_.Exception.Response.StatusCode.value__ "-" $_.ErrorDetails.Message
}
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers   # saldo NAO revertido
Get-Content agencia\data\eventos-agencia-0.jsonl | Select-String "TRANSFERENCIA_FALHOU"
```

## 4. `linha-do-tempo.png`

```powershell
Get-Date
cd agencia
python mesclar_logs.py
```

## 5. `auth-sem-token.png`

```powershell
Get-Date
try {
  Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Method Get
} catch {
  Write-Host "HTTP" $_.Exception.Response.StatusCode.value__ "-" $_.ErrorDetails.Message
}
```

## 6. `auth-com-token.png`

```powershell
Get-Date
$login = Invoke-RestMethod -Uri "http://localhost:4000/auth/login" -Method Post -ContentType "application/json" -Body '{"usuario":"aluno","senha":"senha123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri "http://localhost:4000/contas/0" -Headers $headers
```

## 7. `auth-token-expirado.png`

Suba a Agência 0 **de novo**, em outra porta, com expiração forçada para 0
minutos (não precisa derrubar as outras):

```powershell
Get-Date
$env:JWT_EXPIRACAO_MINUTOS=0; $env:AGENCIA_ID=0; python -m uvicorn src.app:app --port 4010
```

Em outro terminal, alguns segundos depois:

```powershell
Get-Date
$login = Invoke-RestMethod -Uri "http://localhost:4010/auth/login" -Method Post -ContentType "application/json" -Body '{"usuario":"aluno","senha":"senha123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Start-Sleep -Seconds 2
try {
  Invoke-RestMethod -Uri "http://localhost:4010/contas/0" -Headers $headers
} catch {
  Write-Host "HTTP" $_.Exception.Response.StatusCode.value__ "-" $_.ErrorDetails.Message
}
```

## 8. `funcionalidade-adicional.png` (status/health-check)

```powershell
Get-Date
Invoke-RestMethod -Uri "http://localhost:4000/status"
Invoke-RestMethod -Uri "http://localhost:4000/contas" -Method Post -ContentType "application/json" -Headers $headers -Body '{"id":6,"nomeAluno":"Eva","saldoInicial":0}'
Invoke-RestMethod -Uri "http://localhost:4000/status"
```

---

Depois de capturar os prints, adicione-os e feche o sprint:

```powershell
git add evidencias/sprint1
git commit -m "docs(evidencias): adiciona prints das partes D, E, F e da funcionalidade adicional"
git push
```
