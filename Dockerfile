FROM python:3.11-slim AS base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installa dipendenze di sistema per weasyprint e tools necessari
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git ca-certificates \
    # Dipendenze per weasyprint (PDF generation)
    python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 \
    libharfbuzz0b libpangocairo-1.0-0 \
    # Chrome/Chromium per Lighthouse e PDF fallback
    chromium chromium-driver \
    # Node.js per pa11y, axe-core, lighthouse
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installa tools Node.js globalmente con configurazioni per ARM
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
RUN npm install -g pa11y@latest @axe-core/cli@latest lighthouse@latest

# Copia e installa dipendenze Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installa Playwright e i suoi browser 
# Dipendenze complete per Playwright e browser automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-unifont fonts-liberation fonts-dejavu \
    libgdk-pixbuf-xlib-2.0-0 \
    # Dipendenze aggiuntive per browser automation
    xvfb x11-utils \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium \
    && playwright install-deps chromium || true

# Copia il codice dell'applicazione
COPY eaa_scanner/ ./eaa_scanner/
COPY webapp/ ./webapp/
COPY src/ ./src/
COPY *.py ./

# Crea directory necessarie
RUN mkdir -p /app/output /app/logs /app/data

# Variabili d'ambiente di default
ENV OUT_DIR=/app/output \
    REPORT_LANGUAGE=it \
    LOG_LEVEL=INFO \
    PORT=8000 \
    # Path tools
    CHROME_CMD=/usr/bin/chromium \
    PA11Y_CMD=/usr/local/bin/pa11y \
    AXE_CMD=/usr/local/bin/axe \
    LIGHTHOUSE_CMD=/usr/local/bin/lighthouse

# Esponi porta per webapp
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default: avvia webapp FastAPI con Uvicorn
# Migrato da Flask a FastAPI per migliori performance e features moderne
CMD ["python3", "-m", "uvicorn", "webapp.app_fastapi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]