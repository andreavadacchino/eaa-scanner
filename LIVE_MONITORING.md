# Live Monitoring Dashboard - Documentazione Tecnica

Sistema di monitoraggio live per le scansioni di accessibilità EAA implementato con Server-Sent Events (SSE) e interfaccia real-time.

## Architettura

### 1. Backend - Sistema Eventi (SSE)

#### `webapp/scan_monitor.py`
- **`ScanProgressEmitter`**: Gestore centrale eventi con supporto multi-client
- **Eventi supportati**: scan_start, scanner_start, scanner_operation, scanner_complete, scanner_error, page_progress, processing_step, report_generation, scan_complete, scan_failed
- **Memoria eventi**: Buffer circolare con 100 eventi per scan_id
- **Thread safety**: Lock per operazioni concorrenti

#### `webapp/app.py` - Endpoint SSE
- **Route**: `GET /api/scan/stream/{scan_id}`
- **Headers**: Content-Type: text/event-stream, Cache-Control: no-cache
- **Heartbeat**: Ogni 30 secondi per mantenere connessione
- **Formato dati**: JSON over SSE standard

### 2. Integrazione Core Scanner

#### `eaa_scanner/scan_events.py`
- **`ScanEventHooks`**: Wrapper per emettere eventi durante scansione
- **`MonitoredScanner`**: Decorator per scanner esistenti (WAVE, Pa11y, Axe, Lighthouse)
- **Thread-local storage**: Gestione hook per thread di scansione
- **Auto-extract results**: Parsing automatico risultati scanner per summary

#### Modifiche Core
- **`eaa_scanner/core.py`**: Integrazione hooks in run_scan()
- **Parametro `event_monitor`**: Opzionale per abilitare monitoring
- **Wrapping scanner**: Tutti i scanner utilizzano MonitoredScanner
- **Eventi progresso**: Emissione eventi per ogni fase (crawling, scanning, processing, report)

### 3. Frontend - JavaScript Real-time

#### `webapp/static/js/scan_monitor.js`
- **`ScanMonitor`**: Classe principale per interfaccia live
- **EventSource**: Connessione SSE nativa browser
- **Auto-reconnect**: Riconnessione automatica con backoff esponenziale
- **UI dinamica**: Generazione cards scanner, log eventi, progress bars
- **Filtri log**: Sistema filtri per tipi evento
- **Auto-scroll**: Scroll automatico log eventi

#### Componenti UI
- **Header monitor**: Info scansione, stato connessione, durata
- **Scanner grid**: Cards dinamiche per ogni scanner attivo
- **Progress generale**: Barra progresso con operazione corrente
- **Log eventi**: Timeline filtrable con timestamp

### 4. Stili CSS

#### `webapp/static/css/app_v2.css`
- **Responsive design**: Grid adattivo per card scanner
- **Animazioni**: Pulse per scanner attivi, strisce progress bar
- **Stati visivi**: Colori per running/completed/error/critical
- **Accessibilità**: Contrasti appropriati, focus visibili
- **Dark/Light**: Supporto temi (tramite CSS custom properties)

## API Events

### Formato Base Evento
```json
{
  \"event_type\": \"scanner_start\",
  \"timestamp\": \"2024-01-15T14:30:00.000Z\",
  \"scan_id\": \"eaa_20240115_143000_abc123\",
  \"data\": {
    \"scanner\": \"WAVE\",
    \"url\": \"https://example.com\",
    \"message\": \"Avvio WAVE per https://example.com\"
  }
}
```

### Tipi Eventi

#### `scan_start`
```json
{
  \"data\": {
    \"url\": \"https://example.com\",
    \"company_name\": \"ACME Corp\",
    \"scanners_enabled\": {
      \"wave\": true,
      \"pa11y\": true,
      \"axe\": false,
      \"lighthouse\": true
    }
  }
}
```

#### `scanner_start`
```json
{
  \"data\": {
    \"scanner\": \"WAVE\",
    \"url\": \"https://example.com/page1\",
    \"estimated_duration_seconds\": 30
  }
}
```

#### `scanner_complete`
```json
{
  \"data\": {
    \"scanner\": \"WAVE\",
    \"results\": {
      \"errors\": 3,
      \"warnings\": 5,
      \"features\": 2,
      \"timestamp\": 1642261800.123
    }
  }
}
```

#### `page_progress`
```json
{
  \"data\": {
    \"current_page\": 2,
    \"total_pages\": 5,
    \"current_url\": \"https://example.com/products\",
    \"progress_percent\": 40
  }
}
```

## Integrazione Template

### `webapp/templates/index_v2.html`
```html
<!-- Sezione scanning -->
<section id=\"phase-scanning\" class=\"phase-section\">
  <h2>🔎 Scansione Accessibilità in Corso</h2>
  
  <!-- Live Monitor Container -->
  <div id=\"scan-monitor\" class=\"scan-monitor-container\">
    <!-- Contenuto generato dinamicamente da scan_monitor.js -->
  </div>
  
  <!-- Progress tradizionale (mantiene backward compatibility) -->
  <div class=\"scan-progress\">
    <!-- ... -->
  </div>
</section>

<!-- Scripts -->
<script src=\"/static/js/scan_monitor.js\"></script>
<script src=\"/static/js/scanner_v2.js\"></script>
```

### Inizializzazione JavaScript
```javascript
// In scanner_v2.js, dopo avvio scansione:
if (typeof initScanMonitor === 'function') {
  initScanMonitor(this.scanSession, 'scan-monitor');
}
```

## Configurazione Performance

### Server-Side
- **Timeout SSE**: 10 minuti per connessione
- **Buffer eventi**: 100 eventi per scan_id
- **Heartbeat**: 30 secondi
- **Reconnect backoff**: 5s * tentativi (max 10 tentativi)

### Client-Side
- **Polling fallback**: Non necessario con SSE
- **Auto-scroll**: Log con scroll automatico opzionale
- **Filtri eventi**: Rendering condizionale per performance
- **Memory management**: Pulizia eventi vecchi

## Testing

### Script Test
```bash
python3 test_live_monitor.py
```

Verifica:
- ✅ Import moduli
- ✅ Emissione eventi monitor
- ✅ Hook integration
- ✅ MonitoredScanner wrapper
- ✅ File CSS/JS presenti

### Test Manuale
1. Avvia webapp: `python3 webapp/app.py`
2. Vai su `http://localhost:8000/v2`
3. Configura scansione
4. Osserva monitoring live durante esecuzione

## Troubleshooting

### SSE Non Funziona
- **Controllo CORS**: Header Access-Control-Allow-Origin
- **Proxy/Cache**: Nginx/Apache buffering disabilitato
- **Browser Dev Tools**: Network tab per SSE stream

### Eventi Mancanti  
- **Thread hooks**: Verificare set_current_hooks() chiamato
- **Monitor integration**: event_monitor passato a run_scan()
- **Scanner wrapping**: Tutti scanner usano MonitoredScanner

### Performance Issues
- **Troppe connessioni**: Limitare client simultanei
- **Memoria eventi**: Ridurre buffer size se necessario  
- **Network latency**: Aumentare timeout heartbeat

## Estensioni Future

### Possibili Miglioramenti
- **WebSocket upgrade**: Per comunicazione bidirezionale
- **Redis backend**: Per scalabilità multi-istanza
- **Historical replay**: Rivedere scansioni passate
- **Real-time charts**: Grafici aggiornati live
- **Mobile optimizations**: UI responsive migliorata
- **Export events**: Esportazione log eventi

### Metriche Aggiuntive
- **Network timing**: Latenza richieste scanner
- **Resource usage**: CPU/memoria durante scansione  
- **Error rates**: Statistiche errori per scanner
- **Completion rates**: Success rate per tipo pagina

## Note Sicurezza

- **Authentication**: SSE endpoint non protetto (considerare autenticazione)
- **Rate limiting**: Limitare connessioni per IP
- **Data sanitization**: Validazione input eventi
- **CSRF protection**: Token per prevenire attacchi cross-site