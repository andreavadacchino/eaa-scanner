# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ ARCHITETTURA ATTUALE - IMPORTANTE LEGGERE

**STACK IN USO (Gennaio 2025)**:
- **Backend**: FastAPI (`webapp/app_fastapi.py`) - NON Flask/app.py
- **Frontend**: React TypeScript (`webapp/frontend/`) - NON static JS/scanner_v2.js
- **Scanner**: Modalità REALE (simulate=false) - NON simulazione
- **Docker**: `docker-compose.fastapi.yml` - NON altri compose file

**Per dettagli completi vedi: CURRENT_SETUP.md**

## Project Overview

This is an EAA (European Accessibility Act) compliance scanning and reporting system that performs multi-scanner accessibility audits on websites, generating both HTML reports and normalized JSON data. The project is entirely in Italian (code, comments, and reports).

Scrivi sempre in italiano

## Key Commands

### Running Scans
```bash
# Simulate mode (offline, no external API calls)
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --simulate

# Real mode (requires API keys and tools)
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --real

# With WAVE API key
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --real --wave_api_key YOUR_KEY
```

### Web Interface - AGGIORNATO
```bash
# Avvia sistema completo con Docker Compose
docker-compose -f docker-compose.fastapi.yml up

# Frontend React: http://localhost:3000
# Backend FastAPI: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Generate Initial Artifacts
```bash
./generate --all  # Generate REPORT.md, inventory.yaml, findings.csv
./generate --force  # Overwrite existing files
```

### Validate CSV Issues
```bash
make validate
# Or directly:
python3 tools/validate.py data/findings.csv
```

## Architecture

### Core Module Structure
```
eaa_scanner/
├── cli.py          # CLI entry point using argparse
├── config.py       # Configuration management with env vars
├── core.py         # Main orchestration logic
├── processors.py   # Result normalization and scoring
├── report.py       # HTML report generation with Jinja2
├── pdf.py          # PDF generation (Chrome/Chromium)
├── emailer.py      # Email delivery functionality
└── scanners/       # Individual scanner implementations
    ├── wave.py     # WAVE API integration
    ├── axe.py      # Axe-core via subprocess
    ├── lighthouse.py # Lighthouse CLI integration
    └── pa11y.py    # Pa11y CLI integration
```

### Key Components

1. **Scanner Orchestration**: `core.py` coordinates 4 accessibility scanners (WAVE, Axe-core, Lighthouse, Pa11y) in parallel, handling timeouts and fallbacks to simulated data.

2. **Result Normalization**: `processors.py` normalizes results from different scanners into a unified JSON schema with WCAG categorization, severity scoring, and compliance calculation.

3. **Report Generation**: `report.py` uses Jinja2 templates to generate accessible HTML reports with proper table structures, WCAG references, and EAA compliance status.

4. **PDF Generation**: `pdf.py` converts HTML to PDF using headless Chrome/Chromium with fallback to wkhtmltopdf.

## Environment Variables

Key environment variables (can be set in shell or passed as CLI args):
- `WAVE_API_KEY`: WAVE WebAIM API key for real scans
- `PA11Y_CMD`: Override pa11y command (default: tries `pa11y`, `npx pa11y`, `pnpm dlx pa11y`)
- `AXE_CMD`: Override axe command (default: tries `npx @axe-core/cli`, `pnpm dlx @axe-core/cli`)
- `LIGHTHOUSE_CMD`: Override lighthouse command (default: tries `lighthouse`, `npx lighthouse`)
- `CHROME_CMD`: Override Chrome binary for PDF generation

## Scanner Tools Requirements

For real mode scanning:
- **WAVE**: Requires API key (paid service)
- **Pa11y**: Requires Node.js and pa11y CLI (`npm install -g pa11y`)
- **Axe-core**: Requires Node.js and axe-core CLI (`npm install -g @axe-core/cli`)
- **Lighthouse**: Requires Node.js, lighthouse CLI, and Chrome/Chromium

## Output Structure

Scans generate output in `output/eaa_<timestamp>/`:
- `wave.json`, `pa11y.json`, `axe.json`, `lighthouse.json`: Raw scanner outputs
- `summary.json`: Normalized, unified results with compliance scoring
- `report_<company>.html`: Final HTML report
- `api_response.json`: API-style response summary

## Data Formats

### Severity Levels
- `Critical`, `High`, `Medium`, `Low`

### Issue States
- `open`, `in_progress`, `fixed`, `verified`, `wontfix`

### WCAG References
Format: `WCAG 2.2 - X.X.X [Criterion Name]`

### Compliance Levels
- `conforme` / `compliant`
- `parzialmente_conforme` / `partially_compliant`
- `non_conforme` / `non_compliant`

## Testing Approach

The project includes simulated/mock data for offline testing without requiring external APIs or tools. Use `--simulate` flag to test the pipeline without dependencies.

## Important Notes

- All code, comments, and documentation are in Italian
- The system uses a weighted scoring algorithm where critical issues have higher impact on compliance scores
- Scanner results are deduplicated by code+WCAG criterion+source
- The HTML reports are designed to be accessible (proper table structure, captions, scope attributes)
- PDF generation requires either Chrome/Chromium or wkhtmltopdf installed