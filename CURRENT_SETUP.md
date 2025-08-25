# CURRENT SETUP - Sistema EAA Scanner

## 🚀 Architettura Attuale (Gennaio 2025)

### Stack Tecnologico in Produzione

#### Backend: FastAPI
- **Framework**: FastAPI (Python 3.11)
- **File principale**: `webapp/app_fastapi.py`
- **Porta**: 8000
- **Container**: `eaa-scanner-backend`
- **Dockerfile**: `Dockerfile.fastapi`

#### Frontend: React + TypeScript
- **Framework**: React 18 con TypeScript
- **Build tool**: Vite
- **Percorso**: `webapp/frontend/`
- **Porta**: 3000
- **Container**: `eaa-scanner-frontend`
- **Router**: React Router v6

#### Database & Cache
- **Cache**: Redis 7-alpine
- **Container**: `eaa-scanner-redis`
- **Porta**: 6379

### 📁 Struttura Directory

```
accessibility-report/
├── webapp/
│   ├── app_fastapi.py         # Backend FastAPI principale
│   ├── scan_monitor.py        # Sistema SSE per eventi real-time
│   ├── frontend/              # App React
│   │   ├── src/
│   │   │   ├── components/    # Componenti React
│   │   │   ├── api/          # Client API
│   │   │   ├── hooks/        # React hooks
│   │   │   └── stores/       # State management
│   │   ├── vite.config.ts    # Config Vite con proxy
│   │   └── package.json
│   └── static/               # Assets statici (NON React)
│       └── js/
│           └── scanner_v2.js  # Legacy JS (non più usato)
├── eaa_scanner/              # Core scanner logic
│   └── scanners/            # Scanner implementations
├── docker-compose.fastapi.yml # Docker config attuale
└── Dockerfile.fastapi        # Dockerfile backend con scanner
```

### 🐳 Docker Compose Attuale

File: `docker-compose.fastapi.yml`

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.fastapi  # Con scanner reali
    container_name: eaa-scanner-backend
    ports:
      - "8000:8000"
    environment:
      - SIMULATE_MODE=false  # Scanner reali attivi
      
  frontend:
    image: node:18-alpine
    container_name: eaa-scanner-frontend
    working_dir: /app
    volumes:
      - ./webapp/frontend:/app
    ports:
      - "3000:3000"
    environment:
      - VITE_PROXY_TARGET=http://backend:8000
      
  redis:
    image: redis:7-alpine
    container_name: eaa-scanner-redis
    ports:
      - "6379:6379"
```

### 🔧 Scanner Attivi

**Modalità**: PRODUZIONE (non simulazione)
- ✅ **Pa11y**: Installato e funzionante
- ✅ **Axe-core**: Installato e funzionante  
- ✅ **Lighthouse**: Installato e funzionante
- ❌ **WAVE**: Disabilitato (richiede API key)

### 🌐 Endpoints Principali

#### Frontend Routes (React Router)
- `/` - Configuration
- `/discovery` - Page Discovery
- `/selection` - Page Selection
- `/scanning` - Scan Progress
- `/report` - Results Report

#### Backend API (FastAPI)
- `POST /api/scan/start` - Avvia scansione
- `GET /api/scan/{scan_id}/status` - Stato scansione
- `GET /health` - Health check
- `POST /api/discovery/start` - Avvia discovery
- `POST /api/scan/validate` - Valida parametri

### 📝 Note Importanti

1. **NON stiamo usando**:
   - `webapp/app.py` (vecchio Flask)
   - `webapp/static/js/scanner_v2.js` (legacy)
   - Frontend in `frontend/` root (non esiste)

2. **STIAMO usando**:
   - FastAPI backend (`webapp/app_fastapi.py`)
   - React frontend (`webapp/frontend/`)
   - Scanner reali (non simulazione)
   - Docker Compose per orchestrazione

3. **Fix Recenti**:
   - Corretto bug navigazione dopo scansione
   - Attivati scanner reali per produzione
   - Configurato proxy Vite per API calls

### 🚀 Comandi Utili

```bash
# Avvia sistema completo
docker-compose -f docker-compose.fastapi.yml up

# Rebuild dopo modifiche
docker-compose -f docker-compose.fastapi.yml up --build

# Logs
docker logs eaa-scanner-backend
docker logs eaa-scanner-frontend

# Test scanner
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "company_name": "Test", "email": "test@test.com", "simulate": false}'
```

### 🔍 Accesso

- **Frontend React**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

**Ultimo aggiornamento**: Gennaio 2025
**Stato**: PRODUZIONE READY