import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, TrendingUp, BarChart3, Target } from 'lucide-react';
import { motion } from 'framer-motion';
import SearchBar from '@/components/SearchBar';
import { useScraper } from '@/hooks/useScraper';
import ErrorAlert from '@/components/ErrorAlert';

const pageVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { staggerChildren: 0.08, delayChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const scraperMutation = useScraper();

  const handleSearch = async (productName: string, category: string) => {
    setError(null);
    try {
      const result = await scraperMutation.mutateAsync({ productName, category });
      sessionStorage.setItem('scraperResult', JSON.stringify(result));
      sessionStorage.setItem('searchContext', JSON.stringify({ productName, category }));
      sessionStorage.removeItem('analyticsRecommendation');
      sessionStorage.removeItem('marketingStrategy');
      navigate('/results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch product data');
    }
  };

  const features = [
    {
      icon: TrendingUp,
      title: 'Market Analysis',
      description: 'Get comprehensive market insights for your products',
      color: 'cyan',
    },
    {
      icon: BarChart3,
      title: 'Profit Optimization',
      description: 'Find the best wholesale deals and retail opportunities',
      color: 'indigo',
    },
    {
      icon: Target,
      title: 'Strategic Recommendations',
      description: 'AI-powered suggestions to maximize your profits',
      color: 'purple',
    },
  ];

  return (
    <motion.div
      className="relative min-h-screen overflow-hidden bg-transparent"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute right-0 top-36 h-80 w-80 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute bottom-[-6rem] left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-white/5 blur-3xl" />
      </div>

      <div className="container relative z-10 mx-auto px-4 py-16">
        <motion.div className="text-center mb-16" variants={itemVariants}>
          <motion.div className="flex justify-center mb-6" variants={itemVariants}>
            <div className="relative rounded-full border border-white/15 bg-white/10 p-4 shadow-[0_24px_80px_rgba(2,6,23,0.25)] backdrop-blur-xl">
              <Brain className="h-12 w-12 text-cyan-300" />
              <span className="absolute inset-0 rounded-full bg-gradient-to-br from-cyan-400/20 via-transparent to-indigo-400/10" />
            </div>
          </motion.div>
          <motion.h1
            className="mb-6 bg-gradient-to-b from-white via-white to-white/55 bg-clip-text text-6xl font-bold tracking-tighter text-transparent md:text-8xl"
            variants={itemVariants}
          >
            StrategAI
          </motion.h1>
          <motion.p className="mx-auto mb-8 max-w-2xl text-xl text-gray-300" variants={itemVariants}>
            AI-powered E-commerce Profit Optimization Tool
          </motion.p>
          <motion.p className="mx-auto mb-12 max-w-3xl text-lg leading-8 text-gray-400" variants={itemVariants}>
            Discover the best wholesale deals, analyze retail markets, and optimize your profit margins
            with intelligent data-driven insights.
          </motion.p>

          {error && (
            <motion.div className="mx-auto mb-6 max-w-2xl" variants={itemVariants}>
              <ErrorAlert message={error} onClose={() => setError(null)} />
            </motion.div>
          )}

          <motion.div variants={itemVariants}>
            <SearchBar onSearch={handleSearch} isLoading={scraperMutation.isPending} />
          </motion.div>
        </motion.div>

        <motion.div className="mt-20 grid grid-cols-1 gap-8 md:grid-cols-3" variants={pageVariants}>
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const colorClasses = {
              cyan: 'bg-cyan-500/15 border-cyan-500/25 text-cyan-300',
              indigo: 'bg-indigo-500/15 border-indigo-500/25 text-indigo-300',
              purple: 'bg-purple-500/15 border-purple-500/25 text-purple-300',
            };

            return (
              <motion.div
                key={index}
                className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-[0_12px_40px_rgba(2,6,23,0.2)] backdrop-blur-xl"
                variants={itemVariants}
                whileHover={{ y: -4 }}
                transition={{ type: 'spring', stiffness: 260, damping: 24 }}
              >
                <div
                  className={`mb-4 flex w-fit rounded-xl border p-3 backdrop-blur-sm ${colorClasses[feature.color as keyof typeof colorClasses]}`}
                >
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-white">{feature.title}</h3>
                <p className="text-gray-400 leading-7">{feature.description}</p>
              </motion.div>
            );
          })}
        </motion.div>

        <motion.div className="mt-20 text-center" variants={itemVariants}>
          <h2 className="mb-12 text-4xl font-bold text-white md:text-5xl">How It Works</h2>
          <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 md:grid-cols-4">
            {[
              { step: '1', title: 'Enter Product', desc: 'Search for your product' },
              { step: '2', title: 'Data Scraping', desc: 'We analyze wholesale & retail markets' },
              { step: '3', title: 'Analysis', desc: 'Get comprehensive market insights' },
              { step: '4', title: 'Optimize', desc: 'Make data-driven decisions' },
            ].map((item) => (
              <motion.div
                key={item.step}
                className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 text-center shadow-[0_12px_30px_rgba(2,6,23,0.16)] backdrop-blur-xl"
                variants={itemVariants}
                whileHover={{ y: -3 }}
              >
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-white/15 bg-white/10 text-lg font-bold text-white">
                  {item.step}
                </div>
                <h4 className="mb-1 font-semibold text-white">{item.title}</h4>
                <p className="text-sm text-gray-400">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
