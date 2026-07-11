import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Dashboard from './pages/Dashboard';
import Results from './pages/Results';
import Analytics from './pages/Analytics';
import Strategy from './pages/Strategy';
import Visualization from './pages/Visualization';
import Reports from './pages/Reports';
import Marketing from '@/pages/Marketing';
import MarketingHistory from '@/pages/MarketingHistory';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col bg-transparent">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/results" element={<Results />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/strategy" element={<Strategy />} />
            <Route path="/visualization" element={<Visualization />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/marketing" element={<Marketing />} />
            <Route path="/marketing/history" element={<MarketingHistory />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;


