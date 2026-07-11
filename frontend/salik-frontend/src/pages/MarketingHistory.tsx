import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, History } from 'lucide-react';
import { motion } from 'framer-motion';
import Button from '@/components/ui/Button';
import { marketingService } from '@/services/api';

function StatusDot({ status }: { status: string }) {
  const color = status === 'ok' ? 'bg-emerald-400' : status === 'needs_review' ? 'bg-amber-400' : 'bg-red-400';
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />;
}

const pageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { staggerChildren: 0.05, delayChildren: 0.05 },
  },
};

export default function MarketingHistory() {
  const navigate = useNavigate();
  const location = useLocation();
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const analyticsResultId = params.get('analyticsResultId');
    const pipelineRunId = params.get('pipelineRunId');
    const loader = analyticsResultId
      ? marketingService.getHistoryByAnalytics(analyticsResultId, 20)
      : pipelineRunId
        ? marketingService.getHistoryByPipeline(pipelineRunId, 20)
        : marketingService.getHistory(20);

    loader
      .then((data) => setRows(data.strategies))
      .catch((err) => setError(err.message || 'Failed to load history'))
      .finally(() => setLoading(false));
  }, [location.search]);

  const handleRowClick = async (id: string) => {
    try {
      const strategy = await marketingService.getById(id);
      sessionStorage.setItem('marketingStrategy', JSON.stringify(strategy));
      navigate(`/marketing?strategyId=${id}`);
    } catch {
      setError('Failed to load strategy');
    }
  };

  return (
    <motion.div
      className="container mx-auto space-y-6 px-4 py-8"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="h-6 w-6 text-cyan-300" />
          <h1 className="text-3xl font-bold text-white">Marketing History</h1>
        </div>
        <Button variant="outline" onClick={() => navigate('/')}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Dashboard
        </Button>
      </div>

      {loading && <p className="text-gray-400">Loading...</p>}
      {error && <p className="text-red-300">{error}</p>}

      {!loading && rows.length === 0 && (
        <p className="text-gray-400">No strategies generated yet. Run one from the Results page.</p>
      )}

      {rows.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] shadow-[0_16px_40px_rgba(2,6,23,0.16)] backdrop-blur-xl">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-left text-gray-400">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Confidence</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row: any) => (
                <tr
                  key={row.id}
                  className="cursor-pointer border-t border-white/5 transition-colors hover:bg-white/5"
                  onClick={() => handleRowClick(row.id)}
                >
                  <td className="px-4 py-3 font-medium text-white">{row.product_name}</td>
                  <td className="px-4 py-3 text-gray-300">
                    v{row.version_number || 1}
                    {row.is_latest ? ' · latest' : ''}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{row.category}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-2">
                      <StatusDot status={row.analysis_status} />
                      <span className="text-gray-300 capitalize">
                        {row.analysis_status?.replace('_', ' ')}
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {row.confidence_score !== null
                      ? `${(row.confidence_score * 100).toFixed(0)}%`
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(row.created_at).toLocaleDateString('en-PK', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
