# Sistema LLM per EAA Scanner

Estensione del backend Flask per supporto LLM avanzato con OpenAI GPT-4o.

## 🚀 Funzionalità Implementate

### 1. Validazione API Key
- **Endpoint**: `POST /api/llm/validate-key`
- **Cache**: 10 minuti per validazioni
- **Timeout**: 30 secondi
- **Fallback**: Graceful su errore rete

```json
{
  "api_key": "sk-..."
}
```

### 2. Stima Costi Intelligente
- **Endpoint**: `POST /api/llm/estimate-costs`
- **Algoritmo**: Token-based con sconti volumetrici
- **Supporto**: 4 modelli OpenAI
- **Output**: Costi USD/EUR + tempo stimato

```json
{
  "model": "gpt-4o",
  "num_pages": 5,
  "sections": ["executive_summary", "recommendations"],
  "complexity": "medium"
}
```

### 3. Rigenerazione Report
- **Endpoint**: `POST /api/reports/regenerate`
- **Background**: Processing asincrono
- **Tracking**: Progresso real-time
- **Versioning**: Automatico

```json
{
  "scan_id": "ui_1234567890",
  "llm_config": {
    "api_key": "sk-...",
    "model": "gpt-4o",
    "max_tokens": 2000
  },
  "sections": ["executive_summary", "recommendations"]
}
```

### 4. Multi-Versioning Report
- **Endpoint**: `GET /api/reports/{scan_id}/versions`
- **Storage**: In-memory con metadata
- **Download**: `GET /api/reports/{scan_id}/versions/{version}`
- **Formato**: HTML generato on-demand

### 5. Rate Limiting
- **Limite**: 5 richieste/minuto per IP
- **Algoritmo**: Sliding window
- **Response**: 429 Too Many Requests
- **Reset**: Automatico dopo finestra

## 🛠️ Architettura

### Componenti Principali

1. **WebLLMManager** (`webapp/llm_utils.py`)
   - Cache validazioni API key
   - Calcolo costi avanzato
   - Generazione report potenziata
   - Cleanup automatico cache

2. **Rate Limiter** (`webapp/app.py`)
   - Tracking per IP client
   - Window sliding 60 secondi
   - Thread-safe con lock

3. **Task Management**
   - Background workers per LLM
   - Progress tracking real-time
   - Error handling robusto
   - Cleanup automatico

4. **API Extensions** (`webapp/api_extensions.py`)
   - Health check sistema
   - Capabilities discovery
   - Preview sezioni
   - Statistiche utilizzo

### Flusso Operativo

```
1. Frontend → Validazione API Key (cache 10min)
2. Frontend → Stima Costi + Tempo
3. Frontend → Conferma → Avvio Rigenerazione
4. Backend → Worker Thread → Progress Updates
5. Backend → Salvataggio Nuova Versione
6. Frontend → Download Report Potenziato
```

## 📊 Modelli e Prezzi

| Modello | Input ($/1K) | Output ($/1K) | Raccomandato |
|---------|--------------|---------------|--------------|
| gpt-4o | $0.005 | $0.015 | ✅ Primario |
| gpt-4o-mini | $0.00015 | $0.0006 | 💰 Economico |
| gpt-4-turbo | $0.01 | $0.03 | 🚀 Premium |
| gpt-3.5-turbo | $0.0005 | $0.0015 | 📚 Fallback |

## 🔧 Configurazione

### Variabili Ambiente
```bash
OPENAI_API_KEY=sk-...  # Optional, può essere fornita via UI
PORT=8000              # Porta server
```

### Dipendenze Python
```bash
pip install openai>=1.0.0
```

### Sezioni Supportate

| Sezione | Token | Complessità | Descrizione |
|---------|-------|-------------|-------------|
| `executive_summary` | 800 | Bassa | Riassunto per dirigenti |
| `technical_analysis` | 1200 | Alta | Analisi tecnica dettagliata |
| `recommendations` | 1000 | Media | Raccomandazioni prioritizzate |
| `remediation_plan` | 1500 | Alta | Piano correzioni dettagliato |
| `accessibility_statement` | 600 | Bassa | Dichiarazione conformità |
| `compliance_matrix` | 900 | Media | Matrice WCAG dettagliata |
| `user_impact_analysis` | 800 | Media | Impatto categorie utenti |

## 🛡️ Sicurezza e Resilienza

### Rate Limiting
- **Limite**: 5 richieste/minuto per IP
- **Scope**: Solo operazioni costose (validazione, rigenerazione)
- **Bypass**: Possibile per IP whitelist (non implementato)

### Error Handling
- **Circuit Breaker**: Per modelli OpenAI
- **Fallback**: Template locali se LLM non disponibile
- **Timeout**: 30s per singola chiamata
- **Retry**: Con backoff esponenziale

### Validazione Input
- **API Key**: Pattern e test call
- **Token Limits**: Max 4096 per chiamata
- **Sections**: Whitelist predefinita
- **Costs**: Controllo soglie eccessive

### Cache e Performance
- **Validation Cache**: 10 minuti TTL
- **Cost Cache**: Session-based
- **Cleanup**: Automatico ogni ora
- **Memory**: Limit implicito per session count

## 📈 Monitoring e Logging

### Health Check
```bash
curl http://localhost:8000/api/llm/health
```

### Capabilities
```bash
curl http://localhost:8000/api/llm/capabilities
```

### Usage Stats
```bash
curl http://localhost:8000/api/llm/usage-stats
```

### Log Levels
- **INFO**: Operazioni normali
- **WARNING**: Rate limiting, fallback
- **ERROR**: Errori API, validazione fallita
- **DEBUG**: Cache hits, timing (se abilitato)

## 🔄 Integrazione Frontend

### Workflow UI Suggerito

1. **Setup Tab**
   - Input API key
   - Test validazione real-time
   - Selezione modello

2. **Configuration Tab**
   - Selezione sezioni
   - Slider complessità
   - Preview stima costi

3. **Generation Tab**
   - Progress bar real-time
   - Cancel button (UI only)
   - ETA dinamico

4. **Results Tab**
   - Lista versioni
   - Download links
   - Comparison view

### Error States
- **No API Key**: Fallback a template
- **Invalid Key**: Messaggio chiaro + retry
- **Rate Limited**: Countdown timer
- **Generation Failed**: Partial results + retry

## 🧪 Testing

### Unit Tests
```bash
# Test validazione
curl -X POST http://localhost:8000/api/llm/validate-key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "test-key"}'

# Test stima costi
curl -X POST http://localhost:8000/api/llm/estimate-costs \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "sections": ["executive_summary"], "num_pages": 1}'
```

### Load Testing
```bash
# Rate limiting test
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/llm/validate-key \
    -H "Content-Type: application/json" \
    -d '{"api_key": "test"}' &
done
```

## 📝 Estensioni Future

### Priorità Alta
- [ ] Persistent storage per versioni
- [ ] Webhook notifications
- [ ] Batch processing multi-scan
- [ ] Advanced analytics dashboard

### Priorità Media
- [ ] Claude/Anthropic support
- [ ] Custom prompt templates
- [ ] A/B testing sezioni
- [ ] Export formati multipli

### Priorità Bassa
- [ ] Multi-lingua auto-detect
- [ ] OCR integration
- [ ] Voice synthesis
- [ ] Real-time collaboration

## 🐛 Troubleshooting

### Common Issues

**API Key Invalid**
```
Soluzione: Verificare formato sk-* e quota OpenAI
```

**Rate Limited**
```
Soluzione: Attendere reset o implementare queue
```

**Generation Timeout**
```
Soluzione: Ridurre sezioni o aumentare timeout
```

**High Memory Usage**
```
Soluzione: Cleanup cache manuale o restart
```

### Debug Mode
```python
# In app.py
logging.getLogger().setLevel(logging.DEBUG)
```

### Health Monitoring
```bash
# Check sistema
curl http://localhost:8000/api/llm/health | jq

# Monitor memory
ps aux | grep python

# Check logs
tail -f /var/log/eaa-scanner.log
```