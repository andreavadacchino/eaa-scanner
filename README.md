# EAA Scanner - European Accessibility Act Compliance Tool 🇪🇺

Sistema completo di scansione e reporting per la conformità all'European Accessibility Act (EAA 2025).

## Aggiornamento di Stato (2025-08-23)

Modifiche principali per garantire esecuzione reale degli scanner e coerenza API:

- Esecuzione reale di default: `SIMULATE_MODE=false` (la simulazione è solo per testing).
- WAVE: se `WAVE_API_KEY` non è impostata, il toggle WAVE viene disabilitato (nessuna simulazione in produzione).
- Multi‑page: applicazione corretta dei toggles con `ScannerToggles`; rimossi parametri non supportati in `EAAConfig`.
- Endpoint unificato per polling: usare solo `GET /api/scan/status/{session_id}` con supporto `last_event_id` e campo `new_events` nella risposta.
- Contratto risultati: backend e UI usano i dati `aggregated` prodotti dal core (score complessivo, dettagli WCAG, ecc.).
- Eventi Pa11y più robusti: conteggi corretti anche quando i risultati sono in forma `{ "issues": [...] }`.
- Diagnostica: aggiunto `make doctor` per verificare la presenza di Chromium/Chrome e dei CLI (`pa11y`, `@axe-core/cli`, `lighthouse`).
- Pulizia legacy: rimossa la vecchia API Flask non più utilizzata (`webapp/api/*`, `webapp/api_router.py`). Usare FastAPI (`make web-fastapi`).

## 🎯 Features

- **Multi-Scanner Integration**: WAVE, Axe-core, Lighthouse, Pa11y
- **Real-time Progress Monitoring**: SSE (Server-Sent Events) per aggiornamenti live
- **Comprehensive Reporting**: Report HTML interattivi e PDF esportabili
- **WCAG 2.2 Compliance**: Analisi dettagliata secondo gli standard WCAG
- **LLM Integration**: Generazione piani di remediation con AI (OpenAI/Anthropic)
- **Web Interface**: Interfaccia moderna e responsive

## 🚀 Quick Start

### Prerequisiti

- Python 3.10+
- Node.js 16+ (per gli scanner)
- Chrome/Chromium (per PDF generation)

### Installazione

```bash
# Clone repository
git clone https://github.com/yourusername/eaa-scanner.git
cd eaa-scanner

# Installa dipendenze Python
pip install -r requirements.txt

# Installa scanner tools (necessari per modalità reale)
npm install -g pa11y @axe-core/cli lighthouse
```

### Configurazione

1. **API Keys** (opzionale):
```bash
export WAVE_API_KEY="your-wave-api-key"
export OPENAI_API_KEY="your-openai-key"  # Per remediation plans
```

2. **Test rapido** (modalità simulata):
```bash
python3 -m eaa_scanner.cli \
  --url https://example.com \
  --company_name "Test Company" \
  --email test@example.com \
  --simulate
```

## 💻 Utilizzo

### Web Interface (Consigliato)

```bash
# Avvia backend FastAPI e interfaccia web
make doctor         # verifica browser/CLI e variabili
make web-fastapi    # avvia FastAPI su :8000
# Frontend React (dev): vedi sezione Frontend Dev per avvio su :3000 con proxy

# In alternativa (dev all-in-one):
./start_app.sh  # Avvia FastAPI su :8000 e React Dev su :3000
```

### Command Line Interface

```bash
# Scansione reale con tutti gli scanner
python3 -m eaa_scanner.cli \
  --url https://yoursite.com \
  --company_name "Your Company" \
  --email team@yourcompany.com \
  --real \
  --wave_api_key YOUR_KEY

# Modalità simulata per testing (sviluppo)
python3 -m eaa_scanner.cli \
  --url https://example.com \
  --company_name "ACME Corp" \
  --email dev@acme.com \
  --simulate
```

## 📊 Output

Il sistema genera:

- **Report HTML**: Report interattivo con grafici e tabelle
- **PDF Export**: Versione stampabile del report
- **JSON Data**: Dati strutturati per integrazione
- **Summary Metrics**: Punteggio di conformità e metriche aggregate

Output salvato in: `output/eaa_<timestamp>/`

## 🔧 Architettura

```
eaa_scanner/
├── cli.py          # CLI entry point
├── core.py         # Orchestrazione scanner
├── processors.py   # Normalizzazione risultati
├── report.py       # Generazione report HTML
├── scanners/       # Implementazioni scanner
│   ├── wave.py
│   ├── axe.py
│   ├── lighthouse.py
│   └── pa11y.py
└── prompts/        # LLM prompts

webapp/
├── app_fastapi.py     # FastAPI application (principale)
├── app_fastapi_sse.py # Variante SSE
├── frontend/          # App React/Vite
├── static/            # Asset statici
└── templates/         # Template HTML
```

## 🎨 Features Principali

### 1. Discovery Automatica Pagine
- Crawling intelligente del sito
- Selezione pagine da analizzare
- Limiti configurabili

### 2. Monitor Real-time (SSE)
- Progress bar live
- Aggiornamenti per scanner
- Metriche in tempo reale
- Fallback polling automatico

### 3. Report Interattivi
- Grafici conformità WCAG
- Tabelle issues ordinabili
- Export PDF one-click
- Rigenerazione con diversi LLM

### 4. Piani di Remediation AI
- Suggerimenti prioritizzati
- Esempi di codice
- Timeline implementazione
- Stima effort

## 📈 Metriche di Conformità

Il sistema calcola:
- **Punteggio Globale**: 0-100 basato su severità issues
- **Conformità per Livello**: A, AA, AAA
- **Distribuzione Severità**: Critical, High, Medium, Low
- **Trend Temporali**: Confronto tra scansioni

## 🛠️ Development

### Setup Development Environment

```bash
# Crea virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate  # Windows

# Installa in modalità development
pip install -e .
```

### Testing

```bash
# Run tests
pytest tests/

# Test E2E con Playwright
npm run test:e2e

# Lint
flake8 eaa_scanner/
black eaa_scanner/ --check
```

### Frontend Dev (React/Vite)

```bash
cd webapp/frontend
# Avvia dev server su :3000 con proxy verso backend
VITE_PROXY_TARGET=http://localhost:8000 npm run dev

# In alternativa, senza proxy, configura la base URL assoluta
echo 'VITE_API_BASE_URL=http://localhost:8000/api' > .env.development
npm run dev
```

- `VITE_PROXY_TARGET`: URL del backend usato dal proxy Vite per instradare `'/api'` e `'/static'` (default: `http://localhost:8000`).
- `VITE_API_BASE_URL`: base URL per l'API client quando non si usa il proxy (es. build/preview). Esempio: `http://localhost:8000/api`.

### Config Debug (solo sviluppo)

- `DEV_ALLOW_LOCAL_URLS`: se `true/1`, consente discovery e scansione di URL locali (es. `localhost`, `127.0.0.1`, `192.168.*`). Usare solo in ambienti di sviluppo per evitare rischi SSRF.


### Test E2E con Playwright (SPA su :3000)

```bash
# 1) Avvia backend FastAPI
make web &

# 2) Avvia frontend React (porta 3000)
cd webapp/frontend
VITE_PROXY_TARGET=http://localhost:8000 npm run dev &
cd ../..

# 3) Installa browser Playwright (una tantum)
make e2e-setup

# 4) Esegui il full flow test
make e2e
```

### Contributing

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📝 Documentazione

- [SSE Contract](SSE-Contract.md) - Contratto eventi Server-Sent Events
- [Architecture Decision Records](ADR-SSE-Monitor.md) - Decisioni architetturali
- [Test Plan](TESTPLAN-SSE.md) - Piano di test completo

## 🚨 Troubleshooting

### Scanner non trovati
```bash
# Verifica installazione
which pa11y
which lighthouse

# Installa manualmente
npm install -g pa11y @axe-core/cli lighthouse
```

### SSE Connection Issues
- Verifica che il server supporti SSE
- Controlla CORS configuration
- Il sistema fallback automaticamente a polling

### Memory Issues
- Limita numero di pagine per scansione
- Usa `--max-pages` flag
- Monitora con browser DevTools

## 📄 License

MIT License - vedi [LICENSE](LICENSE) per dettagli.

## 🤝 Support

Per problemi o domande:
- Apri una [Issue](https://github.com/yourusername/eaa-scanner/issues)
- Email: support@example.com

## 🙏 Acknowledgments

- WAVE WebAIM per le API di accessibilità
- Deque Systems per Axe-core
- Google per Lighthouse
- Pa11y team per lo scanner open-source

---

**Built with ❤️ for Web Accessibility**

*Ensuring digital inclusion for everyone in compliance with EAA 2025*
