# Integrazione LLM - EAA Scanner

Il sistema EAA Scanner ora supporta l'integrazione con modelli LLM (Large Language Model) per generare contenuti avanzati nei report di accessibilità.

## Funzionalità LLM

### 1. Executive Summary
Genera un riassunto esecutivo basato sui risultati della scansione, includendo:
- Stato generale dell'accessibilità
- Punti critici principali  
- Impatto sulla conformità EAA
- Prossime azioni consigliate

### 2. Raccomandazioni Tecniche
Crea raccomandazioni specifiche e attuabili per ogni tipo di problema rilevato:
- Titolo e priorità della raccomandazione
- Descrizione del problema
- Azioni concrete da implementare
- Riferimenti WCAG pertinenti
- Stima dell'effort richiesto

### 3. Piano di Remediation
Genera un piano strutturato di correzione con:
- Fasi prioritizzate di implementazione
- Timeline realistiche
- Milestone e metriche di successo
- Risorse necessarie
- Gestione dei rischi

## Configurazione

### Variabili d'Ambiente

```bash
# OpenAI API Key (obbligatoria per LLM)
OPENAI_API_KEY=your_api_key_here

# Modelli LLM (opzionali)
LLM_MODEL_PRIMARY=gpt-4o          # Default
LLM_MODEL_FALLBACK=gpt-3.5-turbo  # Default

# Controllo LLM
LLM_ENABLED=true                   # Default: true
```

### Via CLI

```bash
# Con API key OpenAI
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --openai_api_key YOUR_KEY --real

# Disabilitare LLM
python3 -m eaa_scanner.cli --url https://example.com --company_name "ACME" --email team@example.com --llm_enabled false --real
```

## Fallback Graceful

Il sistema funziona correttamente anche **senza API key OpenAI**:

- ✅ **Executive Summary**: Genera riassunto basato su template statistici
- ✅ **Raccomandazioni**: Analizza i pattern degli errori e fornisce raccomandazioni mirate  
- ✅ **Piano Remediation**: Crea piani strutturati basati su punteggio e complessità
- ✅ **Report HTML**: Mantiene tutti i contenuti con indicatori di fallback

## Esempio d'Uso

```python
from eaa_scanner.config import Config
from eaa_scanner.core import run_scan

# Configurazione con LLM abilitato
config = Config(
    url="https://example.com",
    company_name="Azienda Test",
    email="team@azienda.it",
    openai_api_key="your-api-key",  # Opzionale
    llm_model_primary="gpt-4o",     # Opzionale
    llm_enabled=True                # Default: True
)

# Esegue scan con generazione LLM automatica
results = run_scan(config)
```

## Output Report

I report generati includono sezioni arricchite:

### HTML Standard
- **📋 Executive Summary**: Analisi di alto livello
- **💡 Raccomandazioni Tecniche**: Lista prioritizzata con azioni
- **🎯 Piano di Remediation**: Fasi strutturate con timeline
- **✨ Indicatori LLM**: Badge che mostrano quando il contenuto è generato via AI

### Template Jinja2
Il template `report.html.j2` supporta automaticamente:

```jinja2
{% if executive_summary %}
<section>
  <h2>📋 Executive Summary</h2>
  <div class="executive-summary">
    <p>{{ executive_summary }}</p>
    {% if llm_enhanced %}
    <div class="llm-note">✨ Generato automaticamente via AI ({{ llm_model }})</div>
    {% endif %}
  </div>
</section>
{% endif %}
```

## Performance e Costi

### Utilizzo Token (approssimativi)
- **Executive Summary**: ~200-500 token
- **Raccomandazioni Tecniche**: ~400-800 token  
- **Piano Remediation**: ~600-1000 token
- **Totale per report**: ~1200-2300 token

### Tempi di Generazione
- **Con LLM**: +15-30 secondi per report
- **Senza LLM**: Nessun impatto (fallback immediato)

## Troubleshooting

### LLM Non Attivato
```
LLM integration disabilitata o non disponibile
```
**Soluzione**: Verificare `OPENAI_API_KEY` e `LLM_ENABLED=true`

### Errori API OpenAI
```
Errore con modello gpt-4o: Rate limit exceeded
```
**Comportamento**: Fallback automatico a gpt-3.5-turbo, poi a metodi offline

### Contenuto Vuoto
```
LLM ha restituito risposta vuota, uso fallback
```
**Comportamento**: Sistema usa automaticamente template di fallback

## Sicurezza e Privacy

- ✅ **No Data Logging**: I dati non vengono memorizzati da OpenAI
- ✅ **Error Handling**: Gestione sicura degli errori API
- ✅ **Fallback Completo**: Funzionamento garantito anche senza servizi esterni
- ✅ **API Key Sicura**: Gestione tramite variabili d'ambiente

## Modelli Supportati

### OpenAI
- ✅ `gpt-4o` (raccomandato per qualità)
- ✅ `gpt-4-turbo` 
- ✅ `gpt-3.5-turbo` (economico, veloce)

### Personalizzazione
È possibile estendere il sistema per supportare altri provider (Anthropic, Google, etc.) modificando il modulo `llm_integration.py`.