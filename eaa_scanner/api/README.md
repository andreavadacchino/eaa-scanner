# EAA Scanner API - Workflow 2 Fasi

Backend API robusta e scalabile per workflow di scansione accessibilità in 2 fasi:
1. **FASE DISCOVERY**: Scoperta intelligente delle pagine del sito
2. **FASE SCANNING**: Scansione accessibilità delle pagine selezionate

## 🏗️ Architettura

### Componenti Principali

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API REST      │    │   WebSocket      │    │  Session        │
│   Endpoints     │    │   Manager        │    │  Manager        │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ Discovery API   │◄──►│ Real-time Events │◄──►│ Persistent      │
│ Scanning API    │    │ Multi-client     │    │ State           │
│ File Downloads  │    │ Broadcasting     │    │ Recovery        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Discovery       │    │ Scan             │    │ Data Models     │
│ Service         │    │ Service          │    │ & Validation    │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ SmartCrawler    │    │ Multi-Scanner    │    │ Type Safety     │
│ WebCrawler      │    │ Parallel Exec    │    │ Serialization   │
│ Template Detect │    │ Report Gen       │    │ Error Handling  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Stack Tecnologico

- **Backend**: Python 3.11+ con WSGI
- **Crawling**: Playwright (Smart) + requests (fallback)
- **Scanners**: WAVE, Pa11y, Axe-core, Lighthouse
- **WebSocket**: websockets library per real-time
- **Persistenza**: JSON su filesystem con recovery
- **Report**: HTML + PDF generation
- **Logging**: Structured logging con correlation IDs

## 🚀 Quick Start

### 1. Installazione Dipendenze

```bash
# Dipendenze base
pip install requests beautifulsoup4 jinja2

# WebSocket support (opzionale)
pip install websockets

# Playwright per SmartCrawler (opzionale)
pip install playwright
playwright install  # Installa browser
```

### 2. Avvio Server

```python
# Avvio semplice
from eaa_scanner.api.app import AccessibilityAPIServer

server = AccessibilityAPIServer(
    api_host="0.0.0.0",
    api_port=8000,
    websocket_host="localhost", 
    websocket_port=8001
)

server.serve_forever()
```

```bash
# Da command line
python -m eaa_scanner.api.app

# Con variabili ambiente
API_PORT=8080 WS_PORT=8081 python -m eaa_scanner.api.app
```

### 3. Test Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# Avvia discovery
curl -X POST http://localhost:8000/api/discovery/start \
  -H "Content-Type: application/json" \
  -d '{"base_url": "https://example.com"}'

# Controlla status
curl http://localhost:8000/api/discovery/status/{discovery_id}
```

## 📡 API Reference

### Discovery Endpoints

#### `POST /api/discovery/start`
Avvia nuova sessione discovery

**Request:**
```json
{
  "base_url": "https://example.com",
  "config": {
    "max_pages": 50,
    "max_depth": 3,
    "use_smart_crawler": true,
    "screenshot_enabled": true,
    "excluded_patterns": ["\\.(pdf|zip)$"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "discovery_id": "uuid-discovery-session",
  "message": "Discovery avviata",
  "base_url": "https://example.com"
}
```

#### `GET /api/discovery/status/{discovery_id}`
Ottiene status discovery in tempo reale

**Response:**
```json
{
  "session_id": "uuid-discovery-session",
  "base_url": "https://example.com",
  "status": "running",
  "progress_percent": 65,
  "pages_discovered": 23,
  "current_page": "https://example.com/products",
  "templates_detected": 4,
  "errors": [],
  "warnings": []
}
```

#### `GET /api/discovery/results/{discovery_id}`
Ottiene pagine scoperte con metadati

**Query Params:**
- `include_unselected`: boolean (default: true)

**Response:**
```json
{
  "session_id": "uuid-discovery-session",
  "status": "completed",
  "total_pages_discovered": 45,
  "selected_for_scan": 12,
  "pages_by_type": {
    "homepage": [...],
    "contact": [...],
    "form": [...]
  },
  "pages": [
    {
      "url": "https://example.com/contact",
      "title": "Contatti",
      "page_type": "contact",
      "priority": 85,
      "selected_for_scan": true,
      "forms_count": 1,
      "inputs_count": 5,
      "screenshot_path": "path/to/screenshot.png"
    }
  ]
}
```

#### `POST /api/discovery/{discovery_id}/select`
Aggiorna selezione pagine per scanning

**Request:**
```json
{
  "selected_urls": [
    "https://example.com",
    "https://example.com/contact",
    "https://example.com/products"
  ]
}
```

### Scan Endpoints

#### `POST /api/scan/start`
Avvia scansione accessibilità

**Request:**
```json
{
  "discovery_session_id": "uuid-discovery-session",
  "selected_page_urls": [
    "https://example.com",
    "https://example.com/contact"
  ],
  "company_name": "Azienda SRL",
  "email": "admin@azienda.it",
  "config": {
    "scanners_enabled": {
      "wave": true,
      "pa11y": true,
      "axe_core": true,
      "lighthouse": false
    },
    "wave_api_key": "your-wave-api-key",
    "report_type": "professional",
    "simulate": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "scan_id": "uuid-scan-session",
  "message": "Scan avviata",
  "pages_selected": 2
}
```

#### `GET /api/scan/status/{scan_id}`
Ottiene status scan in tempo reale

**Response:**
```json
{
  "session_id": "uuid-scan-session",
  "status": "running",
  "progress_percent": 75,
  "pages_scanned": 3,
  "total_pages": 4,
  "current_page_url": "https://example.com/contact",
  "current_scanner": "Pa11y",
  "total_issues": 15,
  "critical_issues": 2,
  "overall_score": 78,
  "compliance_level": "parzialmente_conforme"
}
```

#### `GET /api/scan/results/{scan_id}`
Ottiene risultati completi scan

**Query Params:**
- `include_issues`: boolean (default: true)

**Response:**
```json
{
  "session_id": "uuid-scan-session",
  "status": "completed",
  "company_name": "Azienda SRL",
  "compliance": {
    "overall_score": 78,
    "compliance_level": "parzialmente_conforme",
    "total_issues": 15,
    "critical_issues": 2,
    "high_issues": 5
  },
  "statistics": {
    "issues_by_severity": {
      "critical": 2,
      "high": 5,
      "medium": 6,
      "low": 2
    },
    "issues_by_wcag_level": {
      "A": 8,
      "AA": 7
    },
    "pages_with_issues": 3
  },
  "reports": {
    "html_available": true,
    "pdf_available": true
  }
}
```

### File Download Endpoints

#### `GET /api/download/html/{scan_id}`
Scarica report HTML

**Response:** File HTML con headers appropriati

#### `GET /api/download/pdf/{scan_id}`
Scarica report PDF

**Response:** File PDF con headers appropriati

#### `POST /api/scan/{scan_id}/generate-pdf`
Genera PDF da HTML esistente

**Response:**
```json
{
  "success": true,
  "message": "PDF generato",
  "pdf_path": "path/to/report.pdf"
}
```

## 🔌 WebSocket Events

### Connessione

```javascript
const ws = new WebSocket('ws://localhost:8001');

// Messaggio di benvenuto
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.event_type === 'connection_established') {
    console.log('Connesso:', data.data.client_id);
  }
};
```

### Sottoscrizione Eventi

```javascript
// Iscriviti a eventi discovery
ws.send(JSON.stringify({
  command: 'subscribe_discovery',
  payload: { session_id: 'uuid-discovery-session' }
}));

// Iscriviti a eventi scan
ws.send(JSON.stringify({
  command: 'subscribe_scan',
  payload: { session_id: 'uuid-scan-session' }
}));
```

### Eventi Real-time

#### Discovery Progress
```json
{
  "event_type": "discovery_progress",
  "session_id": "uuid-discovery-session",
  "timestamp": 1640995200.123,
  "data": {
    "pages_discovered": 23,
    "progress_percent": 65,
    "current_page": "https://example.com/products",
    "page_type": "general"
  }
}
```

#### Discovery Complete
```json
{
  "event_type": "discovery_complete",
  "session_id": "uuid-discovery-session",
  "data": {
    "status": "completed",
    "pages_discovered": 45,
    "templates_detected": 4
  }
}
```

#### Scan Progress
```json
{
  "event_type": "scan_progress",
  "session_id": "uuid-scan-session",
  "data": {
    "pages_scanned": 3,
    "total_pages": 5,
    "progress_percent": 60,
    "current_page": "https://example.com/contact",
    "current_scanner": "WAVE"
  }
}
```

#### Scan Complete
```json
{
  "event_type": "scan_complete",
  "session_id": "uuid-scan-session",
  "data": {
    "status": "completed",
    "overall_score": 78,
    "compliance_level": "parzialmente_conforme",
    "total_issues": 15
  }
}
```

## 🔧 Configurazione Avanzata

### Discovery Configuration

```python
from eaa_scanner.api.models import DiscoveryConfiguration

config = DiscoveryConfiguration(
    max_pages=100,                    # Pagine max da scoprire
    max_depth=3,                      # Profondità max crawling
    timeout_per_page=10000,           # Timeout per pagina (ms)
    use_smart_crawler=True,           # Usa Playwright
    screenshot_enabled=True,          # Salva screenshot
    use_sitemap=True,                 # Cerca sitemap
    follow_external=False,            # Segui link esterni
    excluded_patterns=[               # Pattern da escludere
        r'\.(pdf|zip|exe)$',
        r'/admin/',
        r'/logout'
    ],
    allowed_domains=[                 # Domini aggiuntivi
        'cdn.example.com'
    ]
)
```

### Scan Configuration

```python
from eaa_scanner.api.models import ScanConfiguration

config = ScanConfiguration(
    scanners_enabled={
        'wave': True,                 # Richiede API key
        'pa11y': True,               # Richiede Node.js + pa11y
        'axe_core': True,            # Richiede Node.js + axe
        'lighthouse': False          # Richiede Node.js + lighthouse
    },
    scanner_timeout_ms=30000,         # Timeout per scanner
    parallel_scans=1,                 # Scansioni parallele (futuro)
    report_type="professional",       # standard|professional
    include_screenshots=True,         # Include screenshot
    wave_api_key="your-key-here",     # Chiave WAVE API
    simulate=False                    # Modalità simulazione
)
```

### Environment Variables

```bash
# Server configuration
API_HOST=0.0.0.0                    # Host API
API_PORT=8000                       # Porta API
WS_HOST=localhost                   # Host WebSocket
WS_PORT=8001                        # Porta WebSocket

# Directories
OUTPUT_DIR=./output                 # Directory output
STORAGE_DIR=./output/sessions       # Directory sessioni

# Scanner tools
WAVE_API_KEY=your-wave-key          # Chiave WAVE
PA11Y_CMD=pa11y                     # Comando Pa11y
AXE_CMD="npx @axe-core/cli"          # Comando Axe
LIGHTHOUSE_CMD=lighthouse           # Comando Lighthouse
CHROME_CMD=google-chrome-stable     # Browser per PDF

# Logging
LOG_LEVEL=INFO                      # Livello logging
LOG_FORMAT=structured               # Formato log
```

## 🔄 Stati e Recovery

### Stati Sessione

- `pending`: In attesa di avvio
- `running`: In esecuzione
- `paused`: Pausata (recovery possibile)
- `completed`: Completata con successo  
- `failed`: Fallita con errori
- `cancelled`: Cancellata dall'utente

### Recovery Automatico

Il sistema supporta recovery automatico:

1. **Persistenza**: Tutte le sessioni vengono salvate su disco
2. **Riavvio**: Al riavvio, le sessioni vengono ricaricate
3. **Continuazione**: Le sessioni `paused` possono essere riprese
4. **Cleanup**: Sessioni vecchie vengono rimosse automaticamente

### Gestione Errori

```python
# Esempio gestione errori discovery
try:
    session_id = discovery_service.start_discovery(url, config)
except Exception as e:
    logger.error(f"Discovery fallita: {e}")
    # Il sistema tenta fallback automatico
    # SmartCrawler → WebCrawler → URL singolo
```

## 📊 Monitoring & Metrics

### Health Check

```bash
curl http://localhost:8000/api/health
```

```json
{
  "status": "healthy",
  "timestamp": 1640995200.123,
  "services": {
    "session_manager": true,
    "discovery_service": true,
    "scan_service": true,
    "websocket_manager": true
  },
  "stats": {
    "running_discoveries": 2,
    "running_scans": 1,
    "websocket_connections": 5
  }
}
```

### Statistiche Sistema

```bash
curl http://localhost:8000/api/stats
```

```json
{
  "timestamp": 1640995200.123,
  "session_manager": {
    "discovery_sessions": {
      "total": 47,
      "by_status": {
        "completed": 42,
        "running": 2,
        "failed": 3
      }
    },
    "scan_sessions": {
      "total": 38,
      "by_status": {
        "completed": 35,
        "running": 1,
        "failed": 2
      }
    }
  },
  "websocket_manager": {
    "active_connections": 5,
    "total_connections": 127,
    "events_sent": 1543
  }
}
```

## 🚦 Error Handling

### Codici Errore API

- `400 Bad Request`: Parametri non validi
- `404 Not Found`: Sessione/risorsa non trovata  
- `500 Internal Server Error`: Errore server

### Struttura Errori

```json
{
  "success": false,
  "error": "Messaggio errore user-friendly",
  "code": 400,
  "details": "Dettagli tecnici opzionali"
}
```

### Retry Logic

Il sistema implementa retry automatico per:

- Connessioni di rete (3 tentativi)
- Timeout scanner (2 tentativi)
- Errori temporanei (exponential backoff)

## 🔧 Development

### Setup Development

```bash
# Clone repository
git clone ...
cd accessibility-report

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install playwright websockets
playwright install

# Avvia in modalità development
LOG_LEVEL=DEBUG python -m eaa_scanner.api.app
```

### Testing

```bash
# Test API endpoints
python -m pytest tests/api/

# Test integration
python -m pytest tests/integration/

# Load testing
python tests/load_test.py
```

### Logging

```python
import logging

# Setup logging strutturato
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("Messaggio con context", extra={
    "session_id": "uuid",
    "operation": "discovery",
    "pages_found": 23
})
```

## 📈 Performance

### Ottimizzazioni Implementate

1. **Crawling Parallelo**: SmartCrawler usa Playwright async
2. **Scanner Caching**: Risultati cachati per sessione
3. **Thread Pool**: Operazioni I/O in thread separati
4. **WebSocket Batching**: Eventi raggruppati per efficienza
5. **Session Cleanup**: Rimozione automatica sessioni vecchie

### Benchmark

- **Discovery**: ~50 pagine in 2-3 minuti
- **Scanning**: ~5 pagine in 3-5 minuti (4 scanner)
- **Report Generation**: <30 secondi per 100 issues
- **Memory Usage**: <200MB per sessione media
- **WebSocket Latency**: <50ms per evento

### Limiti Consigliati

- **Max Pages Discovery**: 200 pagine
- **Max Concurrent Sessions**: 10 discovery + 5 scan
- **Max WebSocket Clients**: 50 connessioni
- **Session Retention**: 24 ore

## 🔐 Security

### Misure Implementate

1. **Input Validation**: Tutti gli input validati
2. **Path Traversal Protection**: Prevenzione path traversal
3. **CORS Headers**: Configurazione CORS appropriata
4. **Rate Limiting**: Limite richieste per IP (futuro)
5. **Sanitization**: Sanitizzazione output HTML

### Best Practices

- Non esporre API su internet senza autenticazione
- Usare HTTPS in produzione
- Configurare firewall per WebSocket
- Monitorare logs per attività sospette
- Aggiornare dipendenze regolarmente

## 📄 License

Vedi file LICENSE nel repository.
