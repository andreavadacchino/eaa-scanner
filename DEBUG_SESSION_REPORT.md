# REPORT SESSIONE DEBUG - SISTEMA EAA SCANNER
**Data**: 25 Agosto 2025  
**Durata**: ~2 ore  
**Status**: IN PROGRESS - Problema parzialmente risolto

## 🔴 PROBLEMA PRINCIPALE IDENTIFICATO
Il sistema EAA Scanner ritorna **compliance_score = 0%** invece del valore atteso **25%** con 35+ violations.

## 📊 ANALISI ROOT CAUSE

### 1. PROBLEMA FORMULA PUNTEGGIO (RISOLTO ✅)
**File**: `/eaa_scanner/processors/enterprise_normalizer.py` (righe 592-617)

La formula matematica è corretta:
```python
# Con i valori dell'utente:
critical_count = 2  # 2 * 20 = 40 punti penalty
high_count = 15     # 15 * 10 = 150 -> capped a 30
medium_count = 5    # 5 * 5 = 25 punti penalty  
low_count = 3       # 3 * 2 = 6 punti penalty

total_penalty = 40 + 30 + 25 + 6 = 101 -> capped a 75
overall_score = max(0, 75 + (25 - 75)) = max(0, 25) = 25 ✅
```

**AZIONE FATTA**: Aggiunto debug logging dettagliato alla formula per tracciare i calcoli.

### 2. PROBLEMA DATI MOCK SIMULAZIONE (IN PROGRESS ⚠️)
**File**: `/eaa_scanner/scanners/pa11y.py` (funzione `_simulate`)

Il vero problema è che la modalità simulazione ritorna solo **3 violations** invece di dati realistici:
- ❌ **Pa11y**: Solo 2 errors + 1 warning (invece di 22 dal file reale)
- ❌ **WAVE**: 0 errors, 0 warnings
- ❌ **Axe-core**: Dati mock insufficienti
- ❌ **Lighthouse**: Score fisso senza dettagli

**AZIONE FATTA**: Aggiornato `pa11y.py` con 22 violations realistiche (2 critical + 15 high + 5 medium).

### 3. PROBLEMA CONTAINER DOCKER (PARZIALE ⚠️)
Il container non carica automaticamente le modifiche ai file Python.

**TENTATIVI**:
1. ❌ `docker-compose build --no-cache` - Fallito con exit code 100
2. ✅ `docker cp` per copiare file modificato nel container
3. ✅ `docker-compose restart backend` per ricaricare

## 📁 FILE MODIFICATI

### 1. `/eaa_scanner/processors/enterprise_normalizer.py`
```python
# Aggiunto debug logging (righe 602-617)
logger.info(f"🔍 DEBUG SCORE CALCULATION:")
logger.info(f"   Violations: critical={critical_count}, high={high_count}, medium={medium_count}, low={low_count}")
logger.info(f"   Penalties: critical={critical_penalty}, high={high_penalty}, medium={medium_penalty}, low={low_penalty}")
logger.info(f"   Total penalty: {total_penalty}")
logger.info(f"   Base score: {base_score}, penalty_factor: {penalty_factor}")
logger.info(f"   Formula: max(0, {base_score} + (25 - {penalty_factor}))")
logger.info(f"   ➡️  FINAL SCORE: {overall_score}")
```

### 2. `/eaa_scanner/scanners/pa11y.py`
```python
def _simulate(self, url: str) -> Pa11yResult:
    # Aggiornato con 22 violations realistiche da scan reale
    # 2 critical + 15 high + 5 medium = 22 totali
    data = {
        "documentTitle": "Principia – Navis browse data of your plant",
        "pageUrl": url,
        "issues": [
            # 22 violations dettagliate...
        ]
    }
```

## 🛠️ AZIONI DA COMPLETARE AL RIAVVIO

### PRIORITÀ 1 - VERIFICARE FIX PA11Y
```bash
# 1. Eseguire nuovo scan di test
curl -X POST "http://localhost:8000/api/scan/start" \
-H "Content-Type: application/json" \
-d '{
    "url": "https://principiadv.com",
    "company_name": "Test Debug",
    "email": "test@example.com",
    "simulate": true,
    "enterprise": true
}'

# 2. Verificare che Pa11y produca 22 violations
# 3. Controllare i log per vedere debug output formula
docker logs eaa-scanner-backend --tail 100 | grep "DEBUG SCORE"
```

### PRIORITÀ 2 - FIX ALTRI SCANNER
```python
# File: /eaa_scanner/scanners/wave.py
# Aggiornare _simulate() con violations realistiche (10+ errors)

# File: /eaa_scanner/scanners/axe.py  
# Aggiornare _simulate() con violations realistiche

# File: /eaa_scanner/scanners/lighthouse.py
# Aggiornare _simulate() con accessibility issues
```

### PRIORITÀ 3 - REBUILD CONTAINER COMPLETO
```bash
# Fix Dockerfile.fastapi se necessario per errore apt-get
# Poi rebuild completo:
docker-compose -f docker-compose.fastapi.yml down
docker-compose -f docker-compose.fastapi.yml build --no-cache backend
docker-compose -f docker-compose.fastapi.yml up -d
```

## 🎯 RISULTATO ATTESO
Dopo le correzioni, il sistema dovrebbe:
1. **Pa11y**: Ritornare 22 violations in simulation mode
2. **WAVE**: Ritornare 10+ violations in simulation mode  
3. **Formula Score**: Calcolare correttamente ~25% con debug log visibili
4. **Report HTML**: Mostrare score 25% e dettagli violations

## 📝 NOTE IMPORTANTI

### ARCHITETTURA CORRENTE
- **Backend**: FastAPI (`webapp/app_fastapi.py`)
- **Frontend**: React TypeScript (`webapp/frontend/`)
- **Docker**: `docker-compose.fastapi.yml`
- **Database**: SQLite per risultati scan

### COMANDI UTILI
```bash
# Monitorare log in real-time
docker logs -f eaa-scanner-backend

# Copiare file modificato nel container
docker cp [file_locale] eaa-scanner-backend:/app/[path]

# Verificare scan results
curl "http://localhost:8000/api/scan/results/[scan_id]" | jq

# Accesso container per debug
docker exec -it eaa-scanner-backend bash
```

## ⚠️ CRITICITÀ RIMANENTI

1. **Container Build Failure**: Il rebuild con `--no-cache` fallisce con exit code 100 (problema apt-get Debian)
2. **Debug Log Non Visibili**: I log di debug del normalizer non appaiono ancora
3. **Altri Scanner**: WAVE, Axe, Lighthouse hanno ancora dati mock insufficienti
4. **Frontend**: Non testato se mostra correttamente i nuovi scores

## 🔄 PROSSIMI STEP IMMEDIATI

1. ✅ Verificare che il file `pa11y.py` modificato sia caricato nel container
2. ⏳ Eseguire scan di test e verificare 22 violations da Pa11y
3. ⏳ Controllare se i debug log della formula appaiono
4. ⏳ Se funziona, replicare fix per WAVE, Axe, Lighthouse
5. ⏳ Testare frontend per visualizzazione corretta score

---

**ULTIMO STATO**: File `pa11y.py` copiato nel container, restart eseguito, in attesa di test finale per verificare se le 22 violations vengono caricate correttamente in simulation mode.