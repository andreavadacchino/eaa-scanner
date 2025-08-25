# EAA Scanner Frontend

Un'applicazione React moderna per la scansione di accessibilità web conforme alla Direttiva Europea di Accessibilità (EAA).

## 🚀 Caratteristiche

- **React 18** con TypeScript per type safety
- **Tailwind CSS** per styling moderno e responsive
- **Context API** per gestione stato globale
- **Architettura modulare** con componenti riutilizzabili
- **Gestione errori robusta** con Error Boundaries
- **Polling intelligente** con backoff esponenziale
- **UI accessibile** conforme WCAG 2.1
- **Responsive design** mobile-first

## 📋 Flusso Applicazione

L'applicazione segue un workflow a 5 step:

1. **Configurazione** - Inserimento URL, azienda, email e selezione scanner
2. **Discovery** - Ricerca automatica delle pagine del sito
3. **Selezione** - Scelta delle pagine da scansionare
4. **Scansione** - Esecuzione degli scanner di accessibilità
5. **Report** - Visualizzazione risultati e download PDF/HTML

## 🏗️ Architettura

```
src/
├── components/          # Componenti riutilizzabili
│   ├── common/         # Componenti comuni (LoadingSpinner, Toast, etc.)
│   ├── Layout.tsx      # Layout principale con navigation
│   └── ProgressBar.tsx # Barra di progresso
├── contexts/           # Context per stato globale
│   └── ScanContext.tsx # Stato principale dell'applicazione
├── hooks/              # Hook personalizzati
│   └── useAsyncState.ts # Gestione stato asincrono
├── pages/              # Pagine principali
│   ├── Configuration.tsx # Step 1: Configurazione
│   ├── Discovery.tsx     # Step 2: Discovery pagine
│   ├── Selection.tsx     # Step 3: Selezione pagine
│   ├── Scanning.tsx      # Step 4: Scansione
│   └── Report.tsx        # Step 5: Report risultati
├── services/           # Servizi API
│   └── api.ts          # Client API per backend FastAPI
├── types/              # Definizioni TypeScript
│   └── index.ts        # Tipi dell'applicazione
├── App.tsx             # Componente principale
├── main.tsx            # Entry point
└── index.css           # Stili globali Tailwind
```

## 🛠️ Tecnologie Utilizzate

- **React 18.3** - Framework UI
- **TypeScript 5.4** - Type safety
- **Tailwind CSS 3.4** - Styling
- **React Router 6.23** - Routing
- **Vite 5.2** - Build tool
- **ESLint** - Code linting

## 🚦 Scripts Disponibili

```bash
# Sviluppo
npm run dev

# Build produzione
npm run build

# Preview build
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint
```

## 🔧 Configurazione

### Variabili d'Ambiente

```env
# Backend API URL (default: /api)
VITE_API_BASE_URL=/api

# Ambiente (development/production)
NODE_ENV=development
```

### API Backend

Il frontend comunica con il backend FastAPI su questi endpoint:

- `POST /api/discovery/start` - Avvia discovery pagine
- `GET /api/discovery/status/{id}` - Stato discovery
- `POST /api/scan/multi` - Avvia scansione multi-pagina
- `GET /api/v2/scan/{id}` - Stato scansione
- `GET /api/scan/{id}/report` - Download report

## 🎨 Design System

### Colori

- **Primary**: `#2563eb` (blue-600)
- **Success**: `#22c55e` (green-500)
- **Warning**: `#f59e0b` (yellow-500)
- **Danger**: `#ef4444` (red-500)

### Componenti

- **Layout**: Header con progress indicator e navigazione
- **ProgressBar**: Barra di progresso animata con messaggi
- **Toast**: Notifiche non intrusive
- **ErrorBoundary**: Gestione errori globali
- **LoadingSpinner**: Indicatori di caricamento

## 📱 Responsive Design

- **Mobile-first**: Design ottimizzato per mobile
- **Breakpoints**: sm (640px), md (768px), lg (1024px), xl (1280px)
- **Touch-friendly**: Elementi interattivi dimensionati correttamente
- **Accessibilità**: Focus management, ARIA labels, keyboard navigation

## ♿ Accessibilità

- **WCAG 2.1 AA** compliance
- **Semantic HTML** con ruoli ARIA appropriati
- **Keyboard navigation** completa
- **Focus management** tra i passi
- **Alt text** per tutte le immagini
- **Error messages** chiari e specifici
- **High contrast** support
- **Reduced motion** support

## 🔄 Gestione Stato

### ScanContext

Fornisce stato globale per:
- Step corrente del workflow
- Configurazione scansione
- Pagine scoperte e selezionate
- Risultati scansione
- Hook helpers per validazione e navigazione

### Hook Personalizzati

- `useStepNavigation`: Navigazione tra i passi
- `useConfigValidation`: Validazione configurazione
- `usePageSelection`: Gestione selezione pagine
- `useAsyncState`: Stati asincroni con loading/error

## 🧪 Testing

```bash
# Unit tests (future)
npm run test

# E2E tests (future)
npm run test:e2e

# Coverage
npm run coverage
```

## 🚀 Deployment

### Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### Build Statico

```bash
npm run build
# Output in `dist/`
```

## 🐛 Troubleshooting

### Errori Comuni

1. **CORS**: Verificare configurazione backend
2. **API Timeout**: Aumentare timeout in `api.ts`
3. **Build Errors**: Verificare TypeScript types
4. **Styling**: Controllare Tailwind configuration

### Debug Mode

In development, gli errori mostrano stack trace completi e informazioni tecniche.

## 📝 Note di Sviluppo

- **Strict Mode**: TypeScript in modalità strict
- **Error Boundaries**: Catturano errori React
- **API Polling**: Backoff esponenziale per long-running operations
- **Memory Management**: Cleanup automatico di timeout e listeners
- **Performance**: Code splitting e lazy loading (future)

## 🤝 Contributing

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 Licenza

Questo progetto è sotto licenza MIT. Vedi `LICENSE` per dettagli.