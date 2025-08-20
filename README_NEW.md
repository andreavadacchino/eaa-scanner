# EAA Accessibility Scanner

🏛️ **Sistema professionale di audit accessibilità web multi-scanner conforme a WCAG 2.1/2.2 AA e European Accessibility Act (EAA)**

Questo progetto fornisce un sistema completo per l'analisi automatizzata dell'accessibilità web, utilizzando 4 scanner complementari (WAVE, Pa11y, Axe-core, Lighthouse) per generare report HTML dettagliati e dati normalizzati JSON.

## 🚀 Avvio Rapido

### Prerequisiti
- Python 3.11+
- Node.js 20+ (per Pa11y, Lighthouse, Axe)
- Docker e Docker Compose (opzionale)

### Installazione Locale

```bash
# Clone del repository
git clone <repo-url>
cd accessibility-report

# Ambiente virtuale Python
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Installa dipendenze Python
pip install -r requirements.txt

# Installa tool Node (opzionale per modalità reale)
npm install -g lighthouse@11 pa11y@8 @axe-core/cli@4

# Installa browser per Playwright
python -m playwright install chromium
```

### Installazione Docker

```bash
# Build dell'immagine
docker build -t eaa-scanner .

# Oppure usa docker-compose
docker-compose up --build
```

## 📊 Utilizzo

### Scansione Singolo URL

#### Modalità Simulata (Offline - Default)
```bash
# Non richiede API key o connessione
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --simulate
```

#### Modalità Reale
```bash
# Richiede tool installati e opzionalmente WAVE API key
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --real

# Con WAVE API key
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --real --wave_api_key YOUR_KEY
```

### Scansione Batch da File

```bash
# Da file TXT (una URL per riga)
python3 -m src.app --input samples/urls.txt --company "Azienda Spa" --out-dir reports

# Da file CSV con colonne: url, company_name, email
python3 -m src.app --input urls.csv --out-dir reports

# Da file JSON
python3 -m src.app --input urls.json --out-dir reports
```

### Output Generati

Ogni scansione genera nella cartella `output/eaa_<timestamp>/`:

- **`summary.json`** - Dati normalizzati con schema unificato
- **`report_<company>.html`** - Report HTML professionale e accessibile
- **`wave.json`** - Risultati raw WAVE (se abilitato)
- **`pa11y.json`** - Risultati raw Pa11y
- **`axe.json`** - Risultati raw Axe-core
- **`lighthouse.json`** - Risultati raw Lighthouse
- **`api_response.json`** - Metadata della scansione

## 🔧 Configurazione

### Variabili d'Ambiente (.env)

```bash
# Copia il template
cp .env.example .env

# Modifica con i tuoi valori
nano .env
```

**Configurazioni principali:**

```env
# Scanner (WAVE è opzionale - richiede API key a pagamento)
WAVE_API_KEY=your_wave_api_key
SCANNER_TIMEOUT_MS=60000
REPORT_LANGUAGE=it

# Notifiche Email (opzionale)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM=accessibility@azienda.it
NOTIFY_EMAIL_TO=recipient@example.com

# Notifiche Telegram (opzionale)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Runtime
OUT_DIR=output
LOG_LEVEL=INFO
```

## 🌐 Interfaccia Web

L'applicazione include un'interfaccia web WSGI per eseguire scansioni interattive:

```bash
# Avvia il server web
make web
# oppure
python3 webapp/app.py

# Apri nel browser
http://localhost:8000
```

**Funzionalità Web:**
- Form interattivo per configurare scansioni
- Monitoraggio progresso in tempo reale
- Anteprima report HTML
- Generazione e download PDF
- Storico scansioni

### Generazione PDF

Il sistema supporta generazione PDF tramite:
1. **Chrome/Chromium headless** (preferito)
2. **WeasyPrint** (Python nativo)
3. **wkhtmltopdf** (fallback)

```bash
# Configura Chrome personalizzato (opzionale)
export CHROME_CMD=/usr/bin/google-chrome

# Oppure installa wkhtmltopdf
sudo apt-get install wkhtmltopdf  # Ubuntu/Debian
brew install --cask wkhtmltopdf    # macOS
```

## 📋 Schema Dati Unificato

Il sistema normalizza i risultati di tutti gli scanner in uno schema JSON unificato:

```json
{
  "scan_id": "eaa_1234567890",
  "timestamp": "2024-01-20T10:30:00Z",
  "url": "https://example.com",
  "company_name": "ACME Spa",
  "compliance": {
    "wcag_version": "2.1",
    "wcag_level": "AA",
    "compliance_level": "parzialmente_conforme",
    "eaa_compliance": "partially_compliant",
    "overall_score": 75,
    "categories": {
      "perceivable": {"errors": 5, "warnings": 10},
      "operable": {"errors": 2, "warnings": 5},
      "understandable": {"errors": 1, "warnings": 3},
      "robust": {"errors": 0, "warnings": 2}
    }
  },
  "detailed_results": {
    "errors": [...],
    "warnings": [...],
    "scanner_scores": {
      "wave": 70,
      "pa11y": 75,
      "axe_core": 80,
      "lighthouse": 78
    }
  },
  "recommendations": [...]
}
```

## 🎯 Caratteristiche Principali

### Multi-Scanner Integration
- **WAVE API** - Analisi completa (opzionale, richiede API key)
- **Pa11y** - Test WCAG con Headless Chrome
- **Axe-core** - Regole di accessibilità via Playwright
- **Lighthouse** - Audit accessibilità e performance

### Normalizzazione Intelligente
- Deduplica automatica issues simili
- Mapping criterio WCAG unificato
- Scoring pesato per severità (critical: 20, high: 15, medium: 8, low: 3)
- Categorizzazione POUR (Perceivable, Operable, Understandable, Robust)

### Report Professionali
- HTML accessibile con tabelle strutturate
- Template Jinja2 personalizzabili
- Generazione PDF automatica
- Conformità EAA e riferimenti normativi

### Notifiche Automatiche
- Email SMTP con allegato PDF
- Telegram con riepilogo e metriche
- Webhook personalizzabili

## 🐳 Docker Deployment

```bash
# Build e avvio con docker-compose
docker-compose up -d

# Verifica stato
docker-compose ps

# Logs
docker-compose logs -f eaa-scanner

# Stop
docker-compose down
```

### Docker CLI

```bash
# Scansione singola
docker run --rm -v $(pwd)/output:/app/output \
  --env-file .env \
  eaa-scanner \
  python -m eaa_scanner.cli --url https://example.com --real

# Batch da file
docker run --rm -v $(pwd):/app \
  --env-file .env \
  eaa-scanner \
  python -m src.app --input samples/urls.txt
```

## 🧪 Testing

```bash
# Esegui test unitari
python -m pytest tests/

# Con coverage
python -m pytest --cov=eaa_scanner tests/

# Test specifico
python -m unittest tests.test_normalize
```

## 📚 Architettura

```
eaa_scanner/
├── config.py          # Configurazione Pydantic
├── core.py            # Orchestratore principale
├── processors/        # Normalizzazione risultati
│   ├── normalize.py   # Unificazione e deduplica
│   ├── process_wave.py
│   └── process_pa11y.py
├── scanners/          # Implementazioni scanner
│   ├── wave.py        # WAVE API client
│   ├── pa11y.py       # Pa11y CLI wrapper
│   ├── axe.py         # Axe-core runner
│   └── lighthouse.py  # Lighthouse CLI wrapper
├── report.py          # Generazione HTML
├── pdf.py             # Conversione PDF
├── emailer.py         # Notifiche email
└── notifiers/         # Sistema notifiche
    └── telegram.py
```

## 📁 Struttura Progetto

```
accessibility-report/
├── eaa_scanner/        # Core del sistema
├── src/                # App CLI e utils
├── webapp/             # Interfaccia web WSGI
├── templates/          # Template Jinja2
├── tests/              # Test unitari
├── output/             # Report generati
├── samples/            # File di esempio
├── Dockerfile          # Container Docker
├── docker-compose.yml  # Orchestrazione
├── requirements.txt    # Dipendenze Python
└── .env.example        # Template configurazione
```

## 🛠️ Comandi Utili

```bash
# Genera artefatti iniziali
./generate --all

# Validazione CSV findings
make validate

# Avvia webapp
make web

# Scansione CLI batch
python -m src.app --input urls.txt --out-dir reports

# Test con coverage
python -m pytest --cov=eaa_scanner

# Build Docker
docker build -t eaa-scanner .

# Deploy production
docker-compose up -d --scale eaa-scanner=2
```

## 📏 Standard e Conformità

### Livelli di Severità
- **Critical** - Blocca completamente l'accesso (peso: 20)
- **High** - Impedisce funzionalità importanti (peso: 15)
- **Medium** - Crea difficoltà significative (peso: 8)
- **Low** - Problemi minori (peso: 3)

### Livelli di Conformità
- **Conforme** - Score ≥85, nessun errore critico
- **Parzialmente Conforme** - Score 60-84
- **Non Conforme** - Score <60 o presenza errori critici

### Riferimenti Normativi
- **WCAG 2.1/2.2 Level AA** - Web Content Accessibility Guidelines
- **EN 301 549 v3.2.1** - Standard europeo accessibilità ICT
- **EAA** - European Accessibility Act (Direttiva UE 2019/882)
- **Legge Stanca** - Normativa italiana (L. 4/2004)

## ⚠️ Limitazioni

- I test automatizzati rilevano solo il 30-40% dei problemi di accessibilità
- WAVE richiede API key a pagamento per modalità reale
- Richiede verifica manuale per dichiarazione ufficiale di conformità
- Test con utenti reali e tecnologie assistive sempre raccomandato

## 🤝 Contributi

Contributi benvenuti! Per segnalare bug o proporre miglioramenti:
1. Apri una issue descrivendo il problema/feature
2. Fork del repository
3. Crea branch per la feature (`git checkout -b feature/AmazingFeature`)
4. Commit dei cambiamenti (`git commit -m 'Add AmazingFeature'`)
5. Push al branch (`git push origin feature/AmazingFeature`)
6. Apri Pull Request

## 📄 Licenza

MIT License - vedi file LICENSE per dettagli

## 🙏 Riconoscimenti

- WAVE WebAIM per le API di accessibilità
- Pa11y team per il tool open source
- Deque Systems per Axe-core
- Google per Lighthouse
- Comunità WCAG per gli standard

---

**Sviluppato con ❤️ per un web più accessibile**