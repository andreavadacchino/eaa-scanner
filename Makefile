.PHONY: generate validate web web-wsgi web-fastapi install-deps docker-build docker-run test clean
.PHONY: test-playwright test-quick test-full test-analyze test-setup test-cleanup
.PHONY: e2e e2e-setup e2e-chromium

# Data generation and validation
generate:
	./generate --all

validate:
	python3 tools/validate.py data/findings.csv

# Web server commands
web:
	python3 start_server.py --mode fastapi

web-wsgi:
	python3 webapp/app.py

web-fastapi:
	uvicorn webapp.app_fastapi:app --host 0.0.0.0 --port 8000 --reload

web-production:
	uvicorn webapp.app_fastapi:app --host 0.0.0.0 --port 8000 --workers 4

# Development setup
install-deps:
	pip install -r requirements.txt

install-node-deps:
	npm install -g pa11y @axe-core/cli lighthouse

# Verifica dipendenze runtime (CLI e browser)
.PHONY: doctor
doctor:
	@echo "🔎 Verifica dipendenze runtime..."
	@which pa11y >/dev/null 2>&1 && echo "✅ pa11y: $$(pa11y --version 2>/dev/null || echo present)" || echo "❌ pa11y non trovato (npm i -g pa11y)"
	@which axe >/dev/null 2>&1 && echo "✅ axe-core CLI: $$(axe --version 2>/dev/null || echo present)" || echo "❌ @axe-core/cli non trovato (npm i -g @axe-core/cli)"
	@which lighthouse >/dev/null 2>&1 && echo "✅ lighthouse: $$(lighthouse --version 2>/dev/null || echo present)" || echo "❌ lighthouse non trovato (npm i -g lighthouse)"
	@which chromium >/dev/null 2>&1 && echo "✅ chromium: $$(chromium --version 2>/dev/null || echo present)" || (which google-chrome >/dev/null 2>&1 && echo "✅ chrome: $$(google-chrome --version 2>/dev/null || echo present)" || echo "❌ Chromium/Chrome non trovato")
	@echo "🔧 Variabili ambiente principali:"
	@echo "  SIMULATE_MODE=$${SIMULATE_MODE:-(non impostata)}"
	@echo "  WAVE_API_KEY=$${WAVE_API_KEY:+(impostata)}$${WAVE_API_KEY:-(non impostata)}"
	@echo "  CHROME_CMD=$${CHROME_CMD:-(non impostata)}"
	@echo "  PA11Y_CMD=$${PA11Y_CMD:-(non impostata)}"
	@echo "  AXE_CMD=$${AXE_CMD:-(non impostata)}"
	@echo "  LIGHTHOUSE_CMD=$${LIGHTHOUSE_CMD:-(non impostata)}"

install-test-deps:
	pip install playwright pytest aiohttp
	playwright install

# Docker commands
docker-build:
	docker build -t eaa-scanner .

docker-run:
	docker run -p 8000:8000 -e SIMULATE_MODE=true eaa-scanner

# Testing - Original
test:
	python3 -m pytest tests/ -v

test-scan:
	python3 -m eaa_scanner.cli --url https://example.com --company_name "Test" --email test@example.com --simulate

# Testing - Playwright Suite
test-setup:
	@echo "🔧 Installazione dipendenze test..."
	@pip install playwright aiohttp
	@playwright install chromium
	@mkdir -p screenshots test_reports test_videos
	@echo "✅ Setup test completato"

test-quick:
	@echo "⚡ Esecuzione test rapidi..."
	@python3 test_quick.py

test-full:
	@echo "🚀 Esecuzione test completi Playwright..."
	@python3 test_playwright_complete.py

test-playwright: test-quick test-full

test-analyze:
	@echo "📊 Analisi dei report di test..."
	@if [ -f test_report.json ]; then \
		python3 test_analyzer.py test_report.json; \
	elif [ -f quick_test_report.json ]; then \
		python3 test_analyzer.py quick_test_report.json; \
	else \
		echo "❌ Nessun report di test trovato. Esegui prima 'make test-quick' o 'make test-full'"; \
	fi

test-all: test-setup test-quick test-full test-analyze

test-headless:
	@echo "🤖 Test in modalità headless..."
	@EAA_TEST_HEADLESS=true python3 test_playwright_complete.py

test-demo:
	@echo "🎬 Test demo con modalità lenta..."
	@EAA_TEST_HEADLESS=false EAA_TEST_SLOW_MO=2000 python3 test_playwright_complete.py

# Test con diversi scenari
test-scenarios:
	@echo "🎯 Test con scenari multipli..."
	@for scenario in basic complex government; do \
		echo "Testing scenario: $$scenario"; \
		EAA_TEST_SCENARIO=$$scenario python3 test_quick.py; \
	done

# Test di monitoraggio continuo
test-monitor:
	@echo "📊 Monitoraggio continuo applicazione..."
	@while true; do \
		python3 test_quick.py; \
		sleep 300; \
	done

# Pulizia file di test
test-cleanup:
	@echo "🧹 Pulizia file di test..."
	@rm -rf screenshots/*.png test_videos/*.webm
	@rm -f test_report.json quick_test_report.json *_analysis.json
	@echo "✅ Pulizia test completata"

# Report di test
test-report:
	@echo "📋 Generazione report riepilogativo..."
	@python3 -c "
import json
from pathlib import Path
from datetime import datetime

reports = []
for f in Path('.').glob('*test_report.json'):
    with open(f) as file:
        data = json.load(file)
        reports.append({'file': f.name, 'data': data})

if reports:
    print('📊 RIEPILOGO TEST DISPONIBILI:')
    for r in reports:
        ts = r['data'].get('timestamp', '')
        summary = r['data'].get('summary', {})
        print(f'  {r[\"file\"]}: {summary.get(\"passed\", 0)}/{summary.get(\"total\", 0)} test passati')
else:
    print('❌ Nessun report di test trovato')
"

# Cleanup
clean: test-cleanup
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf output/eaa_* 2>/dev/null || true

# Help
help:
	@echo "🔍 EAA Scanner - Comandi Test Disponibili:"
	@echo ""
	@echo "Setup:"
	@echo "  test-setup      - Installa dipendenze per test Playwright"
	@echo "  install-deps    - Installa dipendenze Python"
	@echo ""
	@echo "Test di base:"
	@echo "  test-quick      - Test rapidi di sanità (30s)"
	@echo "  test-full       - Test completi Playwright (5-10min)"
	@echo "  test-all        - Setup + test rapidi + completi + analisi"
	@echo ""
	@echo "Test avanzati:"
	@echo "  test-headless   - Test in modalità headless (più veloce)"
	@echo "  test-demo       - Test in modalità demo (più lenta, visibile)"
	@echo "  test-scenarios  - Test con scenari multipli"
	@echo "  test-monitor    - Monitoraggio continuo ogni 5 minuti"
	@echo ""
	@echo "Analisi e report:"
	@echo "  test-analyze    - Analizza report esistenti"
	@echo "  test-report     - Mostra riepilogo di tutti i test"
	@echo ""
	@echo "Utilità:"
	@echo "  test-cleanup    - Pulisce file temporanei di test"
	@echo "  clean           - Pulizia completa progetto"
	@echo "  doctor          - Verifica dipendenze runtime (CLI e browser)"
	@echo ""
	@echo "Web server:"
	@echo "  web             - Avvia server automatico"
	@echo "  web-fastapi     - Avvia server FastAPI con reload"
	@echo ""
	@echo "E2E React (porta 3000):"
	@echo "  e2e-setup       - Installa browser Playwright (Chromium)"
	@echo "  e2e             - Esegue test full flow su http://localhost:3000"
	@echo ""
	@echo "Esempio E2E:"
	@echo "  make web &                              # Avvia FastAPI su :8000"
	@echo "  (cd webapp/frontend && VITE_PROXY_TARGET=http://localhost:8000 npm run dev) &"
	@echo "  make e2e                                # Esegui fullflow.spec.ts"

e2e-setup:
	npx playwright install chromium

e2e:
	BASE_URL=http://localhost:3000 npx playwright test webapp/e2e/fullflow.spec.ts --project=chromium
	@echo ""
	@echo "Esempio workflow completo:"
	@echo "  make web &               # Avvia server in background"
	@echo "  make test-setup         # Setup una tantum"
	@echo "  make test-all           # Esegui tutti i test"

# Debug e Bug Fixing
debug-all:
	@echo "🛠️ Esecuzione completa suite di debug..."
	@python3 debug_automation.py

debug-security:
	@echo "🔒 Test di sicurezza..."
	@python3 security_test_suite.py

debug-concurrency:
	@echo "⚡ Test di concorrenza..."
	@python3 concurrency_test_suite.py

debug-integration:
	@echo "🔗 Test di integrazione..."
	@python3 test_complete_system.py

debug-single:
	@echo "🎯 Debug fase singola..."
	@python3 debug_automation.py --phase $(PHASE)

debug-clean:
	@echo "🧹 Pulizia file di debug..."
	@rm -rf debug_reports/
	@rm -f security_test_report.json concurrency_test_report.json
	@rm -f *_analysis.json *_test_report.json

debug-status:
	@echo "📊 Stato debug reports..."
	@ls -la debug_reports/ 2>/dev/null || echo "Nessun report presente"

debug-help:
	@echo "🆘 Comandi Debug Disponibili:"
	@echo "  debug-all       - Esegue tutti i test di debug"
	@echo "  debug-security  - Solo test di sicurezza"
	@echo "  debug-concurrency - Solo test di concorrenza"
	@echo "  debug-integration - Solo test di integrazione"
	@echo "  debug-single    - Singola fase (PHASE=security|concurrency|etc)"
	@echo "  debug-clean     - Pulisce file di debug"
	@echo "  debug-status    - Mostra stato report"

.PHONY: debug-all debug-security debug-concurrency debug-integration debug-single debug-clean debug-status debug-help
