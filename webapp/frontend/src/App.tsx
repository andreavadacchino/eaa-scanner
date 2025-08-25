import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './contexts/AppContext';
import ErrorBoundary from './components/ErrorBoundary';
import Configuration from './pages/Configuration';
import Discovery from './pages/Discovery';
import Selection from './pages/Selection';
import Scanning from './pages/Scanning';
import LLMConfiguration from './pages/LLMConfiguration';
import Report from './pages/Report';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AppProvider>
          <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
            <Routes>
              <Route path="/" element={<Configuration />} />
              <Route path="/discovery" element={<Discovery />} />
              <Route path="/selection" element={<Selection />} />
              <Route path="/scanning" element={<Scanning />} />
              <Route path="/llm-configuration" element={<LLMConfiguration />} />
              <Route path="/report" element={<Report />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </AppProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;