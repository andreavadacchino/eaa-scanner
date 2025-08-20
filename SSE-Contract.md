# SSE Event Contract - EAA Scanner

Contratto definito per gli eventi Server-Sent Events del sistema EAA Scanner.

## Formato Base Evento

Tutti gli eventi SSE seguono questo formato:

```json
{
  "event_type": "string",
  "data": {
    // Event-specific data
  },
  "message": "string (optional)",
  "timestamp": "ISO 8601 timestamp",
  "scan_id": "string"
}
```

## Tipi di Eventi Supportati

### 1. `scan_start`
**Scopo**: Notifica avvio scansione
**Quando**: Immediatamente dopo l'avvio di una scansione

```json
{
  "event_type": "scan_start",
  "data": {
    "company_name": "string",
    "url": "string",
    "total_pages": "number",
    "scanners": ["wave", "pa11y", "axe", "lighthouse"]
  },
  "message": "Scansione avviata",
  "timestamp": "2025-01-20T10:00:00Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Mostra notifica avvio, inizializza contatori

---

### 2. `page_progress`
**Scopo**: Aggiornamento progresso per pagina
**Quando**: Durante la scansione di ogni pagina

```json
{
  "event_type": "page_progress",
  "data": {
    "current_page": 2,
    "total_pages": 5,
    "current_url": "https://example.com/about",
    "progress_percent": 40
  },
  "message": "Scansione pagina 2 di 5",
  "timestamp": "2025-01-20T10:01:30Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Aggiorna barra progresso principale, stato pagina corrente

---

### 3. `scanner_start`
**Scopo**: Avvio scanner specifico su una pagina
**Quando**: All'inizio della scansione di ogni scanner per ogni pagina

```json
{
  "event_type": "scanner_start",
  "data": {
    "scanner": "wave",
    "url": "https://example.com/contact",
    "page_index": 3,
    "estimated_duration": 15000
  },
  "message": "Avvio scanner WAVE",
  "timestamp": "2025-01-20T10:02:00Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Aggiorna card scanner, mostra status attivo

---

### 4. `scanner_operation`
**Scopo**: Operazione dettagliata del scanner
**Quando**: Durante operazioni specifiche del scanner

```json
{
  "event_type": "scanner_operation",
  "data": {
    "scanner": "pa11y",
    "operation": "HTML parsing",
    "url": "https://example.com/services",
    "progress": 60
  },
  "message": "Pa11y: analisi HTML in corso",
  "timestamp": "2025-01-20T10:02:15Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Aggiorna status scanner specifico, log dettagliato

---

### 5. `scanner_complete`
**Scopo**: Completamento scanner su una pagina
**Quando**: Al termine della scansione di un scanner per una pagina

```json
{
  "event_type": "scanner_complete",
  "data": {
    "scanner": "axe",
    "url": "https://example.com/blog",
    "success": true,
    "errors": 3,
    "warnings": 7,
    "duration_ms": 12500,
    "issues_found": [
      {
        "code": "color-contrast",
        "severity": "serious",
        "wcag_criteria": "1.4.3"
      }
    ]
  },
  "message": "Scanner Axe completato",
  "timestamp": "2025-01-20T10:02:45Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Aggiorna metriche errori/warnings, stato pagina completata

---

### 6. `scan_complete`
**Scopo**: Completamento scansione completa
**Quando**: Al termine di tutta la scansione

```json
{
  "event_type": "scan_complete",
  "data": {
    "total_pages_scanned": 5,
    "total_errors": 15,
    "total_warnings": 28,
    "compliance_score": 75,
    "scan_duration_ms": 180000,
    "report_url": "/v2/preview?scan_id=eaa_1234567890",
    "scan_results": {
      // Full results object
      "summary": {...},
      "pages": [...],
      "aggregated_issues": [...]
    }
  },
  "message": "Scansione completata con successo",
  "timestamp": "2025-01-20T10:03:00Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: **TRIGGER TRANSIZIONE AL REPORT** - Chiude SSE, pulisce polling, passa alla fase report

---

### 7. `scan_failed`
**Scopo**: Fallimento scansione
**Quando**: In caso di errore fatale

```json
{
  "event_type": "scan_failed",
  "data": {
    "error": "Network timeout during page scan",
    "error_code": "NETWORK_ERROR",
    "failed_url": "https://example.com/problematic-page",
    "partial_results": true,
    "pages_completed": 2,
    "recovery_suggestion": "Retry scan with fewer pages"
  },
  "message": "Scansione fallita",
  "timestamp": "2025-01-20T10:02:30Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Mostra errore, offre opzioni recovery, reset stato scan

---

### 8. `heartbeat` (opzionale)
**Scopo**: Mantenere connessione alive
**Quando**: Ogni 30-60 secondi durante scansioni lunghe

```json
{
  "event_type": "heartbeat",
  "data": {
    "uptime_ms": 120000,
    "connection_id": "conn_abc123"
  },
  "message": "Connessione attiva",
  "timestamp": "2025-01-20T10:02:00Z",
  "scan_id": "eaa_1234567890"
}
```

**Gestione UI**: Nessuna azione UI, solo mantenimento connessione

## Gestione Errori e Edge Cases

### Eventi Malformati
- **Missing event_type**: Ignora evento, log warning
- **Invalid JSON**: Ignora evento, log error
- **Missing scan_id**: Verifica se corrisponde alla sessione corrente

### Connessione SSE
- **Connection Failed**: Retry con exponential backoff (1s, 2s, 4s, 8s, 16s, 30s)
- **Max Retries Exceeded**: Fallback a polling HTTP
- **Connection Dropped**: Tentativo riconnessione immediato

### Sequenza Eventi
- **Missing scan_start**: Assume avvio in corso
- **Duplicate scan_complete**: Ignora eventi duplicati (idempotenza)
- **Out-of-order events**: Gestisci gracefully, non bloccare UI

## Conformità UI

| Campo Evento | Elemento UI | Azione |
|-------------|-------------|--------|
| `progress_percent` | `.progress-fill` | Aggiorna width |
| `current_page`/`total_pages` | `#pages-progress` | Aggiorna testo |
| `errors`/`warnings` | `#errors-found`, `#warnings-found` | Incrementa contatori |
| `compliance_score` | `#compliance-score` | Aggiorna percentuale |
| `scanner` status | `.scanner-card` | Aggiorna classe CSS |
| `message` | Log console + notification | Mostra toast |
| `scan_complete` | Phase transition | **CRITICAL**: Solo questo evento triggera transizione al report |

## Test Cases Critici

1. **Happy Path**: Tutti gli eventi in sequenza corretta
2. **Network Failure**: Connessione SSE cade durante scan
3. **Scanner Failure**: Singolo scanner fallisce, altri continuano
4. **Malformed Events**: Eventi JSON corrotti
5. **Race Conditions**: Eventi `scan_complete` multipli
6. **Connection Recovery**: Riconnessione dopo drop

## Security Notes

- **No Sensitive Data**: Eventi non devono contenere API keys o dati sensibili
- **Rate Limiting**: Max 10 eventi/secondo per scan_id
- **Validation**: Tutti i campi devono essere sanitized lato server
- **CORS**: Endpoint SSE deve rispettare same-origin policy