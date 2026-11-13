import os

# Define antes de qualquer import de src.config: evita que o app criado em
# nivel de modulo (src.app.app) dispare eleicoes reais durante os testes.
os.environ.setdefault("BULLY_DESLIGADO", "1")
