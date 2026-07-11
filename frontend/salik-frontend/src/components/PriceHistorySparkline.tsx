import { useEffect, useMemo, useState } from 'react';
import { TrendingUp, ArrowUpRight, ArrowDownRight, Clock3 } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { analyticsService } from '@/services/api';
import { PriceHistoryResponse } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Badge from './ui/Badge';

interface PriceHistorySparklineProps {
  productName: string;
  category: string;
  limit?: number;
  className?: string;
  historyData?: PriceHistoryResponse | null;
}

function formatTimestamp(value?: string | null): string {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

function PriceHistoryTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value?: number; name?: string }> }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/95 px-4 py-3 shadow-[0_20px_60px_rgba(2,6,23,0.35)] backdrop-blur-xl">
      {payload.map((entry, index) => (
        <p key={`${entry.name ?? 'value'}-${index}`} className="text-sm text-white">
          <span className="text-gray-400">{entry.name ?? 'Value'}:</span>{' '}
          {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value} PKR
        </p>
      ))}
    </div>
  );
}

export default function PriceHistorySparkline({ productName, category, limit = 12, className, historyData }: PriceHistorySparklineProps) {
  const [data, setData] = useState<PriceHistoryResponse | null>(historyData ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (historyData) {
      setData(historyData);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const load = async () => {
      if (!productName || !category) {
        setData(null);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await analyticsService.getPriceHistory(productName, category, limit);
        if (!cancelled) {
          setData(response);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load price history.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [productName, category, limit, historyData]);

  const chartData = useMemo(() => {
    return (data?.points || []).map((point) => ({
      ...point,
      label: formatTimestamp(point.captured_at),
      spread: Math.max(0, point.retail_avg_price_pkr - point.wholesale_avg_price_pkr),
    }));
  }, [data]);

  const latestPoint = chartData.length ? chartData[chartData.length - 1] : null;
  const earliestPoint = chartData.length ? chartData[0] : null;
  const trendDelta = latestPoint && earliestPoint ? latestPoint.retail_avg_price_pkr - earliestPoint.retail_avg_price_pkr : 0;
  const trendTone = chartData.length < 2 ? 'secondary' : trendDelta > 0 ? 'success' : trendDelta < 0 ? 'warning' : 'secondary';

  if (!productName || !category) return null;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock3 className="h-5 w-5 text-cyan-300" />
          Price History
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" title="Each run is one pipeline execution rolled up from the raw scrape rows.">{data?.total_points || 0} tracked runs</Badge>
          <Badge variant={trendTone === 'success' ? 'success' : trendTone === 'warning' ? 'warning' : 'secondary'} title={chartData.length < 2 ? 'One run is a snapshot, not a trend.' : 'Trend is derived from multiple historical runs.'}>
            {chartData.length < 2 ? 'Snapshot only' : trendDelta > 0 ? 'Retail trend up' : trendDelta < 0 ? 'Retail trend down' : 'Flat trend'}
          </Badge>
        </div>

        <p className="text-xs text-gray-500">Each point is one scrape run; raw supplier and listing rows are rolled into this historical snapshot.</p>

        {loading && <p className="text-sm text-gray-400">Loading historical prices...</p>}
        {error && <p className="text-sm text-amber-300">{error}</p>}
        {!loading && !error && chartData.length === 0 && (
          <p className="text-sm text-gray-400">No historical price runs have been stored yet for this product.</p>
        )}

        {chartData.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Latest wholesale avg</p>
                <p className="mt-1 text-lg font-semibold">{latestPoint?.wholesale_avg_price_pkr.toLocaleString()} PKR</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Latest retail avg</p>
                <p className="mt-1 text-lg font-semibold">{latestPoint?.retail_avg_price_pkr.toLocaleString()} PKR</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Latest spread</p>
                <p className="mt-1 text-lg font-semibold">
                  {latestPoint ? Math.max(0, latestPoint.retail_avg_price_pkr - latestPoint.wholesale_avg_price_pkr).toLocaleString() : '0'} PKR
                </p>
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.14)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<PriceHistoryTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="wholesale_avg_price_pkr"
                    name="Wholesale Avg"
                    stroke="#22d3ee"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="retail_avg_price_pkr"
                    name="Retail Avg"
                    stroke="#818cf8"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="spread"
                    name="Spread"
                    stroke="#34d399"
                    strokeWidth={1.75}
                    strokeDasharray="5 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="flex flex-wrap gap-2 text-xs text-gray-400">
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1">
                <ArrowUpRight className="h-3 w-3 text-cyan-300" />
                Wholesale line
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1">
                <ArrowDownRight className="h-3 w-3 text-indigo-300" />
                Retail line
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-1">
                <TrendingUp className="h-3 w-3 text-emerald-300" />
                Spread line
              </span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
