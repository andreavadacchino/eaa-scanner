# EAA Scanner - Frontend

Modern React frontend for the EAA (European Accessibility Act) compliance scanner with a clear 2-phase workflow for URL discovery and accessibility scanning.

## Architecture Overview

### 🏗️ Technology Stack

- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Full type safety and developer experience
- **Vite** - Fast build tool and development server
- **Tailwind CSS** - Utility-first CSS framework
- **Zustand** - Lightweight state management
- **React Query** - Server state management and caching
- **Framer Motion** - Smooth animations and transitions
- **React Hook Form** - Form handling and validation
- **Socket.io Client** - Real-time WebSocket communication
- **React Hot Toast** - Toast notifications

### 🔧 Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── Layout/          # Header, Sidebar, Layout components
│   │   ├── Workflow/        # Main workflow orchestration
│   │   │   ├── steps/       # Individual workflow steps
│   │   │   ├── ScanWorkflow.tsx
│   │   │   ├── WorkflowHeader.tsx
│   │   │   └── WorkflowNavigation.tsx
│   │   ├── common/          # Reusable UI components
│   │   ├── History/         # Scan history management
│   │   ├── Settings/        # Application settings
│   │   └── Help/           # Help and documentation
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts          # REST API client
│   │   └── websocket.ts    # WebSocket client
│   ├── stores/             # Zustand state stores
│   │   └── scanStore.ts    # Main application state
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts        # All application types
│   ├── hooks/              # Custom React hooks
│   └── utils/              # Utility functions
├── public/                 # Static assets
├── index.html             # HTML entry point
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
└── vite.config.ts         # Vite build configuration
```

## 🚀 Two-Phase Workflow

### Phase 1: URL Discovery
1. **Configuration** - User enters URL, company info, and scan settings
2. **Discovery** - System crawls website and discovers all pages in real-time
3. **Page Analysis** - Automatic categorization and metadata extraction

### Phase 2: Accessibility Scanning
4. **Selection** - User selects pages to scan with smart selection options
5. **Scanning** - Multiple accessibility scanners analyze selected pages
6. **Results** - Comprehensive report with WCAG compliance assessment

## 📡 Real-Time Features

- **Live Discovery Updates** - Pages appear as they're discovered
- **Scan Progress Tracking** - Real-time progress for each page and scanner
- **WebSocket Communication** - Instant updates without polling
- **Connection Status** - Visual indicator of real-time connection

## 🎨 Modern UI Components

### Design System
- **Responsive Design** - Mobile-first approach with breakpoints
- **Accessibility Compliant** - WCAG 2.1 AA compliant interface
- **Dark/Light Themes** - Automatic and manual theme switching
- **Professional Cards** - Clean card-based layout system
- **Interactive Elements** - Hover states, focus rings, transitions

### Component Library
- **StepIndicator** - Visual workflow progress
- **PagesList** - Sortable, filterable page listings
- **ScanProgress** - Real-time scanning visualization
- **ConnectionStatus** - WebSocket connection indicator
- **Smart Selection** - AI-powered page selection interface

## 🔧 State Management

### Zustand Store Structure
```typescript
interface ScanState {
  // Workflow
  currentStep: number
  steps: WorkflowStep[]
  
  // Configuration
  configuration: ScanConfiguration
  
  // Discovery Phase
  discoveryStatus: DiscoveryStatus
  discoveredPages: DiscoveredPage[]
  
  // Selection Phase
  selectedPages: DiscoveredPage[]
  smartSelectionResult: SmartSelectionResult
  
  // Scanning Phase
  scanProgress: ScanProgress
  scanResults: ScanResults
}
```

### Real-Time Updates
- WebSocket events automatically update store
- Optimistic updates for better UX
- Persistent state across browser sessions
- Error recovery and retry mechanisms

## 📊 API Integration

### REST Endpoints
- `POST /api/discovery/start` - Start URL discovery
- `GET /api/discovery/{id}/status` - Get discovery progress
- `POST /api/selection/smart` - Smart page selection
- `POST /api/scan/start` - Start accessibility scan
- `GET /api/scan/{id}/results` - Get scan results

### WebSocket Events
```typescript
// Discovery Events
'discovery_progress' | 'discovery_page_found' | 'discovery_completed'

// Scanning Events  
'scan_progress' | 'scan_page_completed' | 'scan_completed'

// Error Events
'error' | 'connection_status'
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend EAA Scanner running on http://localhost:8000

### Installation
```bash
cd frontend
npm install
```

### Development
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Environment Setup
The frontend expects the backend to be running on `http://localhost:8000` by default. The Vite proxy configuration handles API requests:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  }
}
```

## 🔍 Key Features

### Smart Page Selection
- **WCAG-EM Methodology** - Standards-compliant page sampling
- **Risk-Based Selection** - Prioritize high-risk pages
- **Template Detection** - Automatic grouping of similar pages
- **User Journey Mapping** - Select pages based on user flows

### Real-Time Progress
- **Discovery Visualization** - Live page discovery with metadata
- **Scan Monitoring** - Per-page and per-scanner progress
- **Connection Management** - Automatic reconnection handling
- **Error Recovery** - Graceful error handling and retry

### Professional Reporting
- **Interactive Results** - Filter and explore findings
- **Multiple Formats** - HTML, PDF, JSON, CSV exports
- **Compliance Assessment** - EAA and WCAG conformance
- **Issue Prioritization** - Severity-based issue organization

### Accessibility Features
- **Keyboard Navigation** - Full keyboard accessibility
- **Screen Reader Support** - Proper ARIA labels and structure
- **High Contrast** - Accessible color combinations
- **Focus Management** - Logical focus flow
- **Semantic HTML** - Proper heading structure and landmarks

## 🧪 Testing Approach

### Component Testing
```bash
# Unit tests for components
npm run test:components

# Integration tests for workflows  
npm run test:integration

# E2E tests with Playwright
npm run test:e2e
```

### Testing Strategy
- **Unit Tests** - Individual components and utilities
- **Integration Tests** - Complete workflow testing
- **Visual Testing** - Screenshot regression tests
- **Accessibility Tests** - Automated a11y validation

## 🔧 Configuration

### TypeScript Configuration
- Strict mode enabled for type safety
- Path aliases for clean imports
- Modern ES2022 target with polyfills

### Build Optimization
- Code splitting by route and vendor
- Tree shaking for bundle optimization
- Asset optimization with Vite
- Progressive Web App features ready

## 🚀 Deployment

### Production Build
```bash
npm run build
```

The built application will be in the `dist/` folder, ready for deployment to any static hosting service.

### Integration with Backend
The frontend is designed to work seamlessly with the Python backend. Make sure the backend is configured to:

1. Serve static files from the frontend build
2. Handle WebSocket connections for real-time updates
3. Provide CORS headers for API requests
4. Support the expected API endpoints

## 📝 Development Guidelines

### Code Style
- Use TypeScript strict mode
- Follow React hooks best practices
- Use Tailwind utility classes consistently
- Implement proper error boundaries
- Add proper TypeScript types for all data

### Performance
- Lazy load route components
- Memoize expensive computations
- Optimize re-renders with React.memo
- Use React Query for server state caching
- Implement virtual scrolling for large lists

### Accessibility
- Test with screen readers
- Ensure keyboard navigation
- Use semantic HTML elements
- Provide meaningful alt text
- Maintain logical heading structure

This frontend provides a professional, accessible, and user-friendly interface for the EAA accessibility scanner with real-time updates and a clear two-phase workflow.
