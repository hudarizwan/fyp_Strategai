import { DottedGlowBackground } from './components/ui/dotted-glow-background'
import { NavBar } from './components/ui/tubelight-navbar'
import MagicBento from './components/MagicBento'
import SpotlightCard from './components/SpotlightCard'
import { BentoGrid } from './components/ui/bento-grid'
import { StackedCircularFooter } from './components/ui/stacked-circular-footer'
import { Home, User, Briefcase, FileText, Search, BarChart2, Megaphone, ShieldCheck, Zap, Lightbulb, RefreshCw, UserCheck, Brain } from 'lucide-react'

function App() {
  const navItems = [
    { name: 'Home', url: '#', icon: Home },
    { name: 'Features', url: '#features', icon: Briefcase },
    { name: 'About', url: '#about', icon: User },
    { name: 'Pricing', url: '#pricing', icon: FileText },
  ]



  const capabilities = [
    {
      title: "Autonomous Execution",
      description: "Agents work together with minimal human intervention.",
      icon: <Zap className="w-4 h-4 text-amber-500" />,
      status: "Automated",
      tags: ["Workflow", "Speed"],
      colSpan: 2,
      hasPersistentHover: true,
    },
    {
      title: "Explainable Insights",
      description: "Every recommendation comes with a confidence score and reasoning.",
      icon: <Lightbulb className="w-4 h-4 text-yellow-500" />,
      status: "Transparent",
      tags: ["AI", "Logic"],
      colSpan: 1,
    },
    {
      title: "Real-time Adaptation",
      description: "Systems retrain periodically to stay updated with market shifts.",
      icon: <RefreshCw className="w-4 h-4 text-blue-500" />,
      status: "Adaptive",
      tags: ["Live", "Updates"],
      colSpan: 1,
    },
    {
      title: "Human-in-the-Loop",
      description: "A dedicated dashboard for users to review, edit, and approve AI-generated plans.",
      icon: <UserCheck className="w-4 h-4 text-green-500" />,
      status: "Control",
      tags: ["Review", "Approve"],
      colSpan: 2,
      hasPersistentHover: true,
    },
  ]

  return (
    <div className="relative min-h-screen w-full bg-black overflow-hidden">
      <NavBar items={navItems} />

      {/* Header / Logo & Auth */}
      <div className="absolute top-0 left-0 w-full py-6 px-6 md:px-12 lg:px-24 z-40 flex justify-between items-center pointer-events-none sticky-header-content">
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="w-8 h-8 rounded-lg bg-white/10 border border-white/20 flex items-center justify-center backdrop-blur-md">
            <Brain className="h-5 w-5 text-cyan-400" />
          </div>
          <span className="text-xl font-bold text-white tracking-tight">StrategAi</span>
        </div>

        <div className="flex items-center gap-4 pointer-events-auto">
          <button className="text-sm font-medium text-gray-300 hover:text-white transition-colors">
            Log In
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-white text-black rounded-full hover:bg-gray-100 transition-colors">
            Sign Up
          </button>
        </div>
      </div>

      <DottedGlowBackground className="absolute inset-0 w-full h-full z-0 pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-white px-4">
        <div className="mb-8 p-4 bg-white/10 border border-white/20 backdrop-blur-md rounded-full">
          <Brain className="h-12 w-12 text-cyan-400" />
        </div>
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter mb-6 bg-clip-text text-transparent bg-gradient-to-b from-white to-white/50 pb-4">
          StrategAi
        </h1>
        <p className="text-xl md:text-2xl text-gray-400 max-w-2xl text-center mb-10">
          An Agentic AI platform that autonomously scrapes market data, predicts optimal pricing, and generates ROI-driven marketing strategies.
        </p>
        <a
          href="http://localhost:5173"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block relative z-[60] pointer-events-auto px-8 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-full backdrop-blur-sm transition-all text-white font-medium cursor-pointer no-underline text-center"
        >
          Found Your Product
        </a>
      </div>

      <div className="relative z-20 bg-black pt-24 pb-12 flex flex-col items-center">
        <h2 className="text-4xl md:text-5xl font-bold text-center text-white mb-16">
          Complexity, Refined
        </h2>
        <MagicBento />
      </div>

      <div className="relative z-20 bg-black pt-10 pb-12 flex flex-col items-center px-4">
        <h2 className="text-4xl md:text-5xl font-bold text-center text-white mb-6">
          See the Agents in Action
        </h2>
        <p className="text-xl text-gray-400 max-w-3xl text-center mb-16">
          Watch how our autonomous agents work together to process millions of data points and deliver a cohesive, actionable business strategy in minutes.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full max-w-7xl">
          {/* Card 1: Scraper Agent */}
          <SpotlightCard className="custom-spotlight-card border-white/10 bg-white/5" spotlightColor="rgba(255, 255, 255, 0.25)">
            <div className="relative z-20 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center mb-6">
                  <Search className="w-6 h-6 text-cyan-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Scraper Agent</h3>
                <p className="text-gray-400">
                  Automatically crawls wholesale and retail platforms for live market data.
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-white/10 flex justify-between items-center">
                <span className="text-sm text-cyan-400 font-medium">Crawling</span>
                <span className="text-xs text-gray-500">v2.4.0</span>
              </div>
            </div>
          </SpotlightCard>

          {/* Card 2: Analytics Agent */}
          <SpotlightCard className="custom-spotlight-card border-white/10 bg-white/5" spotlightColor="rgba(255, 255, 255, 0.25)">
            <div className="relative z-20 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-full bg-indigo-500/20 flex items-center justify-center mb-6">
                  <BarChart2 className="w-6 h-6 text-indigo-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Analytics Agent</h3>
                <p className="text-gray-400">
                  Uses ML models (XGBoost & Random Forest) to predict the most profitable price points.
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-white/10 flex justify-between items-center">
                <span className="text-sm text-indigo-400 font-medium">Analyzing</span>
                <span className="text-xs text-gray-500">v3.1.2</span>
              </div>
            </div>
          </SpotlightCard>

          {/* Card 3: Marketing Agent */}
          <SpotlightCard className="custom-spotlight-card border-white/10 bg-white/5" spotlightColor="rgba(255, 255, 255, 0.25)">
            <div className="relative z-20 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center mb-6">
                  <Megaphone className="w-6 h-6 text-purple-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">Marketing Agent</h3>
                <p className="text-gray-400">
                  Designs campaign plans focused on maximum Return on Investment (ROI).
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-white/10 flex justify-between items-center">
                <span className="text-sm text-purple-400 font-medium">Designing</span>
                <span className="text-xs text-gray-500">v1.8.5</span>
              </div>
            </div>
          </SpotlightCard>

          {/* Card 4: MCB Decision Agent */}
          <SpotlightCard className="custom-spotlight-card border-white/10 bg-white/5" spotlightColor="rgba(255, 255, 255, 0.25)">
            <div className="relative z-20 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center mb-6">
                  <ShieldCheck className="w-6 h-6 text-emerald-400" />
                </div>
                <h3 className="text-2xl font-bold text-white mb-4">MCB Decision Agent</h3>
                <p className="text-gray-400">
                  A validation layer that only recommends strategies with a confidence score ≥ 0.70.
                </p>
              </div>
              <div className="mt-8 pt-6 border-t border-white/10 flex justify-between items-center">
                <span className="text-sm text-emerald-400 font-medium">Validating</span>
                <span className="text-xs text-gray-500">v4.0.1</span>
              </div>
            </div>
          </SpotlightCard>
        </div>
      </div>

      <div className="relative z-20 bg-black pt-10 pb-24 flex flex-col items-center">
        <h2 className="text-4xl md:text-5xl font-bold text-center text-white mb-16">
          Platform Capabilities
        </h2>
        <BentoGrid items={capabilities} />
      </div>

      <StackedCircularFooter />
    </div>
  )
}

export default App
