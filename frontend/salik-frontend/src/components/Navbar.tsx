import { Link, useLocation } from 'react-router-dom';
import { Brain, BarChart3, Target, TrendingUp, FileText, Home, History } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/results', label: 'Results', icon: BarChart3 },
  { path: '/analytics', label: 'Analytics', icon: TrendingUp },
  { path: '/strategy', label: 'Strategy', icon: Target },
  { path: '/visualization', label: 'Visualization', icon: BarChart3 },
  { path: '/reports', label: 'Reports', icon: FileText },
  { path: '/marketing/history', label: 'History', icon: History },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/85 backdrop-blur-2xl supports-[backdrop-filter]:bg-slate-950/65">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/15 bg-white/10 backdrop-blur-xl shadow-[0_0_0_1px_rgba(255,255,255,0.04)]">
              <Brain className="h-5 w-5 text-cyan-300 transition-transform duration-300 group-hover:scale-110" />
              <span className="absolute inset-0 rounded-xl bg-gradient-to-br from-cyan-400/20 via-transparent to-indigo-400/15 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            </div>
            <span className="text-xl font-semibold tracking-tight text-white">
              StrategAI
            </span>
          </Link>

          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 backdrop-blur-xl">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'relative flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition-colors duration-300',
                    isActive ? 'text-white' : 'text-gray-400 hover:text-white'
                  )}
                >
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="pointer-events-none absolute inset-0 rounded-full border border-cyan-400/20 bg-white/10 shadow-[0_0_24px_rgba(34,211,238,0.12)]"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                  <Icon className="relative z-10 h-4 w-4" />
                  <span className="relative z-10 hidden md:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}


