FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
ENV DATA_DIR=/dados
VOLUME /dados
# a porta de cada agencia e PORTA_BASE + AGENCIA_ID (4000, 4001, 4002)
CMD ["sh", "-c", "exec uvicorn src.app:app --host 0.0.0.0 --port $((PORTA_BASE + AGENCIA_ID))"]
