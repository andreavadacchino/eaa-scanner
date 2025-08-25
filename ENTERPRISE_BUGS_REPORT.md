# 🚨 REPORT CRITICO: Bug Sistema Enterprise EAA Scanner

**Data**: 25 Agosto 2025  
**Autore**: Analisi Critica Sistema  
**Severità**: **CRITICA** - Sistema NON utilizzabile in produzione

## 📊 Executive Summary

Il sistema di aggregazione enterprise presenta **difetti fondamentali** che rendono i report generati **inaffidabili e potenzialmente fuorvianti**. I test su domini reali (beinat.com, google.com, example.com) hanno rivelato:

1. **Scanner non funzionanti** (Pa11y, Axe)
2. **Calcolo score matematicamente errato**
3. **Aggregazione dati incoerente**
4. **Dati falsi/simulati nel codice**

## 🔴 PROBLEMI CRITICI IDENTIFICATI

### 1. SCANNER NON FUNZIONANTI

#### Pa11y
- **Errore**: `Error: Cannot find module 'pa11y'`
- **Causa**: Pa11y NON installato nel container Docker
- **Impatto**: Nessun dato da Pa11y, ma sistema riporta "success" con score 100

#### Axe-core
- **Errore**: `error: unknown option '--no-sandbox,--disable-setuid-sandbox...'`
- **Causa**: Parametri Chrome passati erroneamente ad Axe CLI
- **Impatto**: Nessun dato da Axe, ma sistema riporta "success" con score 100

#### WAVE
- **Errore**: `WAVE API key not provided`
- **Causa**: Nessuna API key configurata
- **Impatto**: Fallback silenzioso, nessun dato WAVE

### 2. FORMULA CALCOLO SCORE ERRATA

**File**: `eaa_scanner/processors/enterprise_normalizer.py`  
**Linea**: 614

```python
# FORMULA ATTUALE (SBAGLIATA)
overall_score = max(0, base_score + (25 - penalty_factor))
```

**Problemi**:
- Può generare score > 100 (se penalty_factor < 25)
- Non segue standard WCAG
- Logica arbitraria senza documentazione

**Esempio concreto**:
- Base score: 85
- Nessun errore → penalty_factor = 0
- Score finale = 85 + 25 = **110** (impossibile!)

### 3. AGGREGAZIONE DATI INCOERENTE

#### Deduplica Errata
```python
# Linea 156 in enterprise_normalizer.py
if issue['code'] not in seen_codes:
    unique_issues.append(issue)
```

**Problema**: Deduplica solo per 'code', perdendo:
- Selettori HTML diversi
- Contesto diverso
- Posizione nella pagina

**Risultato**: 10 errori diversi diventano 1 solo

#### Conteggi Non Corrispondenti
- Somma errori per categoria: 73
- Totale errori riportato: 50
- **Differenza**: 23 errori persi!

### 4. DATI HARDCODED/SIMULATI

**File**: `eaa_scanner/enterprise_core.py`

```python
# Esempi trovati:
"ejemplo.com"  # URL fake
"Test Company S.p.A."  # Azienda fake
DEFAULT_SCORE = 75  # Valore arbitrario
```

### 5. MANCANZA TOTALE DI TEST

- **0 test unitari** per il sistema enterprise
- **0 test di integrazione**
- **0 validazione** dei calcoli
- Solo script manuali senza asserzioni

## 📈 EVIDENZE DAI TEST REALI

### Test su beinat.com
```json
{
  "scanner_results": {
    "pa11y": "FAILED - Module not found",
    "axe": "FAILED - Wrong parameters",
    "lighthouse": "SUCCESS - Found violations",
    "wave": "FAILED - No API key"
  },
  "reported_score": 59,
  "expected_score": "Non calcolabile con 2/4 scanner falliti",
  "compliance": "non_conforme"
}
```

## 🔧 CORREZIONI NECESSARIE

### PRIORITÀ 1 - IMMEDIATA
1. **Installare Pa11y nel Docker container**
   ```dockerfile
   RUN npm install -g pa11y
   ```

2. **Correggere parametri Axe**
   ```python
   # Rimuovere parametri Chrome da axe_cmd
   axe_cmd = ["npx", "@axe-core/cli", url]  # Non aggiungere --no-sandbox etc
   ```

3. **Fix formula calcolo score**
   ```python
   # Formula corretta WCAG-based
   def calculate_wcag_score(violations):
       weights = {
           'critical': 25,
           'serious': 15, 
           'moderate': 5,
           'minor': 1
       }
       total_penalty = sum(weights.get(v.severity, 0) for v in violations)
       score = max(0, min(100, 100 - total_penalty))
       return score
   ```

### PRIORITÀ 2 - URGENTE
1. **Implementare validazione input**
   ```python
   from pydantic import BaseModel, validator
   
   class ScannerOutput(BaseModel):
       violations: List[Violation]
       
       @validator('violations')
       def validate_violations(cls, v):
           # Validazione struttura
           return v
   ```

2. **Correggere deduplica**
   ```python
   def deduplicate_smart(violations):
       seen = set()
       unique = []
       for v in violations:
           key = f"{v.code}:{v.selector}:{v.context}"
           if key not in seen:
               unique.append(v)
               seen.add(key)
       return unique
   ```

3. **Aggiungere test reali**
   ```python
   def test_score_calculation():
       violations = [
           {'severity': 'critical', 'count': 2},
           {'severity': 'serious', 'count': 3}
       ]
       score = calculate_wcag_score(violations)
       assert 0 <= score <= 100
       assert score == expected_value
   ```

### PRIORITÀ 3 - IMPORTANTE
1. Rimuovere TUTTI i dati hardcoded
2. Documentare formule e algoritmi
3. Implementare logging dettagliato
4. Aggiungere metriche di quality assurance

## 🚫 RACCOMANDAZIONI

### NON USARE IN PRODUZIONE
Il sistema nella sua forma attuale:
- Genera report **inaffidabili**
- Può dare **falsi positivi** (siti con problemi marcati come conformi)
- Può dare **falsi negativi** (siti conformi marcati come non conformi)
- **Non rispetta** gli standard WCAG

### AZIONI IMMEDIATE
1. **STOP** all'uso del sistema per clienti reali
2. **Audit completo** del codice
3. **Reimplementazione** della logica di aggregazione
4. **Testing estensivo** prima del rilascio

## 📝 CONCLUSIONE

Il sistema enterprise di aggregazione è **fondamentalmente compromesso** e richiede una **revisione completa** prima di poter essere utilizzato in modo affidabile. I problemi identificati non sono semplici bug ma **difetti architetturali** che richiedono riprogettazione.

**Tempo stimato per correzione completa**: 2-3 settimane
**Rischio se usato ora**: CRITICO - possibili implicazioni legali per report errati

---

*Questo report è stato generato attraverso analisi critica del codice e test su domini reali. Tutti i problemi sono verificabili e riproducibili.*