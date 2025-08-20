# EAA Scanner - European Accessibility Act Compliance Tool 🇪🇺

Sistema completo di scansione e reporting per la conformità all'European Accessibility Act (EAA 2025).

## 🎯 Features

- **Multi-Scanner Integration**: WAVE, Axe-core, Lighthouse, Pa11y
- **Real-time Progress Monitoring**: SSE (Server-Sent Events) per aggiornamenti live
- **Comprehensive Reporting**: Report HTML interattivi e PDF esportabili
- **WCAG 2.2 Compliance**: Analisi dettagliata secondo gli standard WCAG
- **LLM Integration**: Generazione piani di remediation con AI (OpenAI/Anthropic)
- **Web Interface**: Interfaccia moderna e responsive

## 🚀 Quick Start

### Prerequisiti

- Python 3.8+
- Node.js 16+ (per gli scanner)
- Chrome/Chromium (per PDF generation)

### Installazione

```bash
# Clone repository
git clone https://github.com/yourusername/eaa-scanner.git
cd eaa-scanner

# Installa dipendenze Python
pip install -r requirements.txt

# Installa scanner tools (opzionale per modalità real)
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
# Avvia server web
make web
# Oppure
python3 webapp/app.py

# Apri browser su http://localhost:8000
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

# Modalità simulata per testing
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
├── app.py          # Flask application
├── static/         # Frontend assets
│   ├── css/
│   └── js/
│       ├── scanner_v2.js     # Main UI controller
│       └── scan_monitor_fixed.js  # SSE monitor
└── templates/      # HTML templates
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
