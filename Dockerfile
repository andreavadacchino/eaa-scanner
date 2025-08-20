FROM python:3.11-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installa dipendenze di sistema base
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Crea directory output
RUN mkdir -p /app/output

# Variabili d'ambiente di default
ENV OUT_DIR=/app/output \
    REPORT_LANGUAGE=it \
    LOG_LEVEL=INFO

# Esponi porta per webapp
EXPOSE 8000

# Default: avvia webapp WSGI
CMD ["python", "-m", "webapp.app"]