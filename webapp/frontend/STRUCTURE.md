# Struttura Frontend EAA Scanner v3.0

Frontend React completamente riscritto con architettura semplice e pulita.

## 📁 Struttura File System

```
webapp/frontend/
├── public/
├── src/
│   ├── components/          # Componenti riusabili
│   │   ├── Layout.tsx      # Layout principale con progress indicator
│   │   └── ProgressBar.tsx # Barra di progresso animata
│   ├── contexts/           # State management
│   │   └── ScanContext.tsx # Context principale con hooks
│   ├── pages/              # Pagine del flusso
│   │   ├── Configuration.tsx # Step 0: Form configurazione
│   │   ├── Discovery.tsx     # Step 1: Ricerca pagine
│   │   ├── Selection.tsx     # Step 2: Selezione pagine
│   │   ├── Scanning.tsx      # Step 3: Scansione in progress
│   │   └── Report.tsx        # Step 4: Visualizzazione risultati
│   ├── services/           # API layer
│   │   └── api.ts          # Client API con polling intelligente
│   ├── types/              # TypeScript definitions
│   │   └── index.ts        # Tutti i tipi dell'app
│   ├── App.tsx             # Router principale
│   ├── main.tsx            # Entry point React
│   └── index.css           # Tailwind + custom CSS
├── package.json            # Dependencies (minimali)
├── tsconfig.json           # TypeScript config
├── vite.config.ts          # Vite config con proxy API
├── tailwind.config.js      # TailwindCSS config
├── .env                    # Environment variables
├── README.md               # Documentazione
└── STRUCTURE.md            # Questo file
```

## 🔄 Flusso Applicazione

```
Configuration → Discovery → Selection → Scanning → Report
     ↓             ↓          ↓          ↓         ↓
  Form init    Auto start  Multi-sel  Polling   Download
   Step 0       Step 1      Step 2     Step 3    Step 4
```

## 🧩 Architettura Componenti

### Context API (State Management)
- **ScanContext**: Stato globale dell'applicazione
- **Custom Hooks**: useStepNavigation, useConfigValidation, usePageSelection

### API Service Layer
- **apiService**: Singleton per chiamate API
- **Polling Intelligente**: Backoff esponenziale 1s→30s
- **Error Handling**: Retry automatici e graceful degradation
- **Timeout Management**: 30s/120s per diversi endpoint

### Layout & UI
- **Layout**: Header con progress, contenuto responsive
- **ProgressBar**: Componente riusabile animato
- **TailwindCSS**: Utility-first styling

## 📡 Integrazione API

### Endpoints Utilizzati
```
POST /api/discovery/start     → Avvia ricerca pagine
GET  /api/discovery/status/   → Status discovery (polling)
POST /api/v2/scan            → Avvia scansione singola
POST /api/scan/multi         → Avvia scansione multi-pagina
GET  /api/v2/scan/{id}       → Status scansione (polling)
GET  /api/scan/{id}/report   → Download report
```

### Polling Strategy
```javascript
Backoff: 1s → 2s → 4s → 8s → 16s → 30s (max)
Retry: 3 tentativi per errori di rete
Timeout: Discovery ~10min, Scanning ~20min
```

## 🎯 Features Implementate

### ✅ Core Features
- [x] Workflow completo 5 step
- [x] Gestione robusta lunghe attese
- [x] Context API per state management
- [x] TypeScript type safety
- [x] Responsive design
- [x] Error handling completo
- [x] Polling con backoff esponenziale
- [x] Download report PDF/HTML
- [x] Validazione form real-time

### ✅ Integrazione Backend
- [x] FastAPI REST API
- [x] Discovery automatica pagine
- [x] Multi-page scanning
- [x] Scanner reali (Pa11y, Axe, Lighthouse)
- [x] Report generation
- [x] Progress tracking real-time

### ✅ UX/UI
- [x] Progress indicator visibile
- [x] Feedback durante attese lunghe
- [x] Gestione errori user-friendly  
- [x] Mobile responsive
- [x] Accessibilità WCAG compliant
- [x] Loading states e animazioni

## 🚀 Bundle Info

```
Build Size: 206KB gzipped (~62KB compressed)
CSS: 18KB (TailwindCSS purged)
Modules: 43 transformed
Build Time: <1s
```

## 🔧 Comandi Utili

```bash
npm run dev          # Dev server su :3000
npm run build        # Build produzione
npm run type-check   # TypeScript validation
npm run lint         # ESLint check
```

## 🐳 Docker Integration

Il frontend si integra perfettamente con il sistema Docker:
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000` (proxy automatico)
- **Build Output**: `../static/react/` per servire via FastAPI

---

**Versione**: 3.0.0  
**Data**: Gennaio 2025  
**Stack**: React 18 + TypeScript + TailwindCSS + Vite
