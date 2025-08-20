# Accessibility Report — PDR esecutivo per Codex CLI

> **Lingua**: tutto in italiano (codice, commenti, report).  
> **Scopo**: generare in locale, senza n8n, un sistema di audit accessibilità multi‑scanner che produca un **documento HTML professionale** e un **JSON normalizzato** per ogni URL.

---
## 1) Obiettivo & Contesto
Realizzare un’app **Python 3.11** orchestrata da **Typer** che:
- legge una o più URL (input via CLI, CSV, JSON);  
- esegue 4 scanner: **WAVE API**, **axe-core** (via Playwright), **Lighthouse** (CLI), **Pa11y** (opzionale/CLI);  
- normalizza i risultati in uno **schema unico JSON**;  
- genera un **report HTML (Jinja2)** conforme a WCAG 2.1/2.2 AA + note EAA;  
- invia facoltativamente notifiche **email** e **Telegram**;  
- è **Docker-ready**.

Vincoli:
- Nessun affidamento a n8n.  
- Comandi riproducibili da CLI locale o `docker compose`.

---
## 2) Stack tecnico
- **Python 3.11**: `typer`, `pydantic`, `jinja2`, `requests`, `rich`, `python-dotenv`, `aiohttp`, `pandas` (facolt.), `weasyprint` (facolt. PDF).  
- **Node 20** per tool CLI: `lighthouse`, `pa11y`, `axe-core` (via Playwright in Python), `playwright` (install browser Chromium).  
- **Chromium** per Lighthouse/Playwright.  
- **Docker**: base `python:3.11-slim`, install Node + Chromium + Playwright.

---
## 3) Struttura file attesa (da generare)
```
accessibility-report/
├─ src/
│  ├─ app.py
│  ├─ config.py
│  ├─ scanners/
│  │  ├─ wave.py
│  │  ├─ axe.py
│  │  ├─ lighthouse.py
│  │  └─ pa11y.py
│  ├─ normalizer/
│  │  └─ normalize.py
│  ├─ notifiers/
│  │  ├─ notify_email.py
│  │  └─ notify_telegram.py
│  └─ utils/
│     ├─ io.py
│     └─ slug.py
├─ templates/
│  └─ report.html.j2
├─ samples/
│  └─ urls.txt
├─ tests/
│  └─ test_normalize.py
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml
├─ .env.example
└─ README.md
```

---
## 4) Variabili d’ambiente (`.env.example`)
```
# Scanner
WAVE_API_KEY=changeme
REPORT_LANGUAGE=it

# Notifiche (opzionali)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASS=password
SMTP_FROM=accessibility@azienda.it
NOTIFY_EMAIL_TO=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Runtime
OUT_DIR=reports
LOG_LEVEL=INFO
```

---
## 5) requirements.txt (Python)
```
Typer[all]==0.12.3
pydantic==2.7.4
jinja2==3.1.4
requests==2.32.3
aiohttp==3.9.5
rich==13.7.1
python-dotenv==1.0.1
pandas==2.2.2
weasyprint==62.3  # opzionale per PDF
```

> Nota: `playwright` lo installiamo in Docker con `pip` + `playwright install chromium`.

---
## 6) Dockerfile
```
FROM python:3.11-slim AS base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# dipendenze di sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git ca-certificates gnupg unzip \
    chromium chromium-common chromium-driver \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Node 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

# Tool CLI Node (lighthouse, pa11y)
RUN npm i -g lighthouse@11 pa11y@8

# app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir playwright==1.46.0 \
    && python -m playwright install --with-deps chromium

COPY . .

ENV OUT_DIR=/app/reports

CMD ["python", "-m", "src.app"]
```

---
## 7) docker-compose.yml
```
version: "3.9"
services:
  accessibility:
    build: .
    env_file: .env
    volumes:
      - ./:/app
    command: ["python", "-m", "src.app", "--input", "samples/urls.txt", "--out-dir", "reports"]
```

---
## 8) Template HTML (`templates/report.html.j2`)
Creare un template **semplice ma accessibile** (contrasto, caption, scope). Minimo:
```
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Report accessibilità – {{ company }}</title>
  <style>
    body {background:#fff;color:#000;font-family:Arial, sans-serif;line-height:1.6;margin:2rem;}
    h1,h2,h3 {color:#003366;margin-top:1.5rem;}
    table {width:100%;border-collapse:collapse;margin:1rem 0;}
    th,td {border:1px solid #000;padding:.5rem;text-align:left;}
    th {background:#f2f2f2;font-weight:bold;}
    caption {font-weight:bold;text-align:left;margin:.5rem 0;}
    .prio-high{color:#c00;font-weight:bold}.prio-medium{color:#c60}.prio-low{color:#666}
  </style>
</head>
<body>
  <header>
    <h1>Report di accessibilità – {{ company }}</h1>
    <p><strong>URL:</strong> {{ url }} · <strong>Data:</strong> {{ date }} · <strong>Score complessivo:</strong> {{ compliance.overall_score }}/100</p>
  </header>

  <section>
    <h2>Stato di conformità</h2>
    <p>Classificazione: <strong>{{ compliance.compliance_level }}</strong> (EAA: {{ compliance.eaa_compliance }})</p>
    <table aria-describedby="desc-conformita">
      <caption>Riepilogo per principi WCAG</caption>
      <thead>
        <tr><th scope="col">Area</th><th scope="col">Errori</th><th scope="col">Avvisi</th></tr>
      </thead>
      <tbody>
        {% for area,vals in compliance.categories.items() %}
          {% if (vals.errors + vals.warnings) > 0 %}
          <tr><td>{{ area }}</td><td>{{ vals.errors }}</td><td>{{ vals.warnings }}</td></tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Problemi prioritari</h2>
    <ul>
    {% for rec in recommendations %}
      <li class="prio-{{ 'high' if rec.priority=='alta' else ('medium' if rec.priority=='media' else 'low') }}">
        <strong>{{ rec.title }}</strong> — {{ rec.description }}
      </li>
    {% endfor %}
    </ul>
  </section>

  <section>
    <h2>Dettaglio problemi</h2>
    <table>
      <caption>Top 20 problemi</caption>
      <thead>
        <tr>
          <th scope="col">Tipo</th>
          <th scope="col">Descrizione</th>
          <th scope="col">WCAG</th>
          <th scope="col">Scanner</th>
          <th scope="col">Occorrenze</th>
        </tr>
      </thead>
      <tbody>
        {% for i in detailed_results.errors[:20] %}
        <tr>
          <td>Errore</td>
          <td>{{ i.description }}</td>
          <td>{{ i.wcag_criteria }}</td>
          <td>{{ i.source }}</td>
          <td>{{ i.count or 1 }}</td>
        </tr>
        {% endfor %}
        {% for i in detailed_results.warnings[:10] %}
        <tr>
          <td>Avviso</td>
          <td>{{ i.description }}</td>
          <td>{{ i.wcag_criteria }}</td>
          <td>{{ i.source }}</td>
          <td>{{ i.count or 1 }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
</body>
</html>
```

---
## 9) Schema dati unificato (output JSON per URL)
```
{
  "scan_id": "str",
  "timestamp": "ISO-8601",
  "url": "str",
  "company_name": "str|null",
  "compliance": {
    "wcag_version": "2.1",
    "wcag_level": "AA",
    "compliance_level": "conforme|parzialmente_conforme|non_conforme",
    "eaa_compliance": "compliant|partially_compliant|non_compliant",
    "overall_score": 0-100,
    "categories": {"perceivable":{"errors":0,"warnings":0},"operable":{},"understandable":{},"robust":{}}
  },
  "detailed_results": {
    "errors": [ {"source":"WAVE|Axe-Core|Lighthouse|Pa11y","severity":"critical|high|medium|low","code":"str","description":"str","count":1,"wcag_criteria":"1.4.3","remediation":"str"} ],
    "warnings": [ ... ],
    "features": [ ... ],
    "scanner_scores": {"wave":0-100,"pa11y":0-100,"axe_core":0-100,"lighthouse":0-100}
  },
  "recommendations": [ {"priority":"alta|media|bassa","title":"str","description":"str","actions":["str", "str"]} ],
  "raw_scanner_data": {"wave":{}, "pa11y":{}, "axe_core":{}, "lighthouse":{}}
}
```

---
## 10) Specifica moduli
### `src/config.py`
- Carica `.env` (dotenv), valida con Pydantic.
- Espone `Settings` (WAVE key, SMTP, Telegram, OUT_DIR, REPORT_LANGUAGE, LOG_LEVEL).

### `src/utils/slug.py`
- `slugify(url|company)` per nomi file.

### `src/utils/io.py`
- Lettura `--input` (txt/csv/json), deduplica, validazione URL.

### `src/scanners/wave.py`
- `async def run(url, api_key) -> dict`: chiama `https://wave.webaim.org/api/request?key=...&url=...&reporttype=4&format=json` e ritorna JSON.

### `src/scanners/axe.py`
- Usa **Playwright** (Python) e **axe-core** iniettato come script; esponi `async def run(url) -> dict` con `{violations:[...], passes:[...]}` (ridotto).

### `src/scanners/lighthouse.py`
- Esegue `lighthouse <url> --quiet --only-categories=accessibility --chrome-flags=--headless --output=json --output-path=stdout` via `asyncio.create_subprocess_exec`; ritorna dict con `accessibility.score` e `audits`.

### `src/scanners/pa11y.py` (opz.)
- Esegue `pa11y <url> --reporter json` e ritorna issues.

### `src/normalizer/normalize.py`
- Funzione `def normalize(results: dict, meta: dict) -> dict` che unisce i 4 scanner e calcola:
  - deduplica per `code+wcag+source`;
  - pesi severità: `critical=20, high=15, medium=8, low=3`;  
  - `overall_score = max(0, 100 - penalty)`;  
  - mappa per principi WCAG (1→perceivable, 2→operable, 3→understandable, 4→robust);
  - genera `recommendations` (contrasto, alt text, struttura, forms) come da n8n.

### `src/notifiers/notify_email.py`
- `def send_email(html: str, subject: str, to: str, settings: Settings) -> None` via SMTP STARTTLS.

### `src/notifiers/notify_telegram.py`
- `def send_message(text: str, settings: Settings) -> None` via `https://api.telegram.org/botTOKEN/sendMessage`.

### `src/app.py`
- CLI Typer:
  - `--url` singola o `--input` lista; `--out-dir` (default `reports`); `--email-to`; `--telegram` boolean.  
  - Per ogni URL: esegui **in parallelo** (async) WAVE + axe + lighthouse (+ pa11y), poi `normalize`, salva `*.json` e `*.html` (Jinja2).  
  - Stampa riepilogo con `rich`.

---
## 11) Test (`tests/test_normalize.py`)
- Testa che `normalize` calcoli `overall_score` coerente, categorizzi 1.x→perceivable, deduplichi duplicati.

---
## 12) Comandi di sviluppo
```bash
# locale
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)  # oppure usare python-dotenv
python -m src.app --url https://example.org --out-dir reports

# docker
docker build -t accessibility:dev .
docker run --rm -it --env-file .env -v "$PWD":/app accessibility:dev \
  python -m src.app --input samples/urls.txt --out-dir reports

# compose
docker compose up --build
```

---
## 13) Criteri di accettazione
- [ ] Per 1 URL viene generato **JSON normalizzato** e **HTML report** in `reports/`.
- [ ] WAVE viene chiamato via API key da `.env` e gli errori di rete sono gestiti.
- [ ] Lighthouse/axe/pa11y falliscono in modo **graceful** (timeout, exit code) senza bloccare l’intero batch.
- [ ] `overall_score` ∈ [0,100] e cambia al variare del numero/severità problemi.
- [ ] Template HTML usa tabelle con `caption` e `th scope="col"`.
- [ ] Opzione `--email-to` invia email con HTML inline; `--telegram` invia messaggio di riepilogo.
- [ ] Docker image eseguibile su macchina pulita (solo Docker necessario).

---
## 14) Nota sulla conformità normativa
Il report deve includere nei testi fissi riferimenti a **WCAG 2.1/2.2 AA**, **EN 301 549 v3.2.1**, e menzione dell’**European Accessibility Act (EAA)** come cornice regolatoria; chiarire che la valutazione automatizzata richiede verifica manuale per la dichiarazione ufficiale.

---
## 15) Prompt operativo per Codex CLI
> **Istruzione:** Genera **tutti i file** indicati nella struttura (se mancanti) e implementa i moduli secondo le specifiche sopra. Inserisci docstring e commenti in italiano. Dove indicato, crea stubs minimi funzionanti. Implementa controllo errori/retry basilari per chiamate esterne (HTTP/CLI) e timeouts.
