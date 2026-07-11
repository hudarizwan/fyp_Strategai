import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ScraperResponse } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { normalizeScraperResult } from '@/utils/normalizeScraperResult';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const COLORS = ['#22d3ee', '#818cf8', '#c084fc', '#fb7185', '#34d399', '#f59e0b'];

const pageVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { staggerChildren: 0.08, delayChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
};

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number | string; name?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/95 px-4 py-3 shadow-[0_20px_60px_rgba(2,6,23,0.35)] backdrop-blur-xl">
      {label && <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-gray-400">{label}</p>}
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <p key={`${entry.name ?? 'value'}-${index}`} className="text-sm text-white">
            <span className="text-gray-400">{entry.name ?? 'Value'}:</span>{' '}
            {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value} PKR
          </p>
        ))}
      </div>
    </div>
  );
}

export default function Visualization() {
  const [data, setData] = useState<ScraperResponse | null>(null);

  useEffect(() => {
    const storedData = sessionStorage.getItem('scraperResult');
    if (storedData) {
      try {
        const parsed = normalizeScraperResult(JSON.parse(storedData));
        setData(parsed);
      } catch (err) {
        console.error('Failed to parse data:', err);
      }
    }
  }, []);

  if (!data) {
    return (
      <div className="container mx-auto min-h-[calc(100vh-8rem)] px-4 py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-400">
              No visualization data available. Please search for a product first.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const wholesaleItems = data.wholesale.made_in_china || [];
  const retailItems = data.retail || [];

  const wholesaleData = wholesaleItems.map((item, index) => ({
    name: `Supplier ${index + 1}`,
    'Unit Price (PKR)': item.unit_price_pkr,
    MOQ: item.moq,
  }));

  const retailData = retailItems.map((item) => ({
    name: item.platform,
    'List Price (PKR)': item.list_price,
  }));

  const platformData = retailItems.reduce((acc: any, item) => {
    const existing = acc.find((p: any) => p.name === item.platform);
    if (existing) {
      existing.value += 1;
    } else {
      acc.push({ name: item.platform, value: 1 });
    }
    return acc;
  }, []);

  const priceRangeData = [
    {
      name: 'Wholesale',
      Min: Math.min(...wholesaleItems.map((w) => w.unit_price_pkr)),
      Max: Math.max(...wholesaleItems.map((w) => w.unit_price_pkr)),
      Avg:
        wholesaleItems.reduce((sum, w) => sum + w.unit_price_pkr, 0) / wholesaleItems.length,
    },
    {
      name: 'Retail',
      Min: Math.min(...retailItems.map((r) => r.list_price)),
      Max: Math.max(...retailItems.map((r) => r.list_price)),
      Avg: retailItems.reduce((sum, r) => sum + r.list_price, 0) / retailItems.length,
    },
  ];

  const profitData = wholesaleItems.map((w, index) => {
    const minRetail = Math.min(...retailItems.map((r) => r.list_price));
    return {
      name: `Supplier ${index + 1}`,
      'Profit Potential': Math.max(0, minRetail - w.unit_price_pkr),
    };
  });

  const axisTick = { fill: '#94a3b8', fontSize: 12 };
  const gridStroke = 'rgba(148, 163, 184, 0.14)';

  return (
    <motion.div
      className="container mx-auto space-y-8 px-4 py-8"
      initial="hidden"
      animate="visible"
      variants={pageVariants}
    >
      <motion.div className="mb-6" variants={itemVariants}>
        <h1 className="mb-2 text-3xl font-bold text-white">Data Visualization</h1>
        <p className="text-gray-400">
          Interactive charts and graphs for {data.product_name}
        </p>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle>Wholesale Price Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={wholesaleData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
              <YAxis tick={axisTick} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Bar dataKey="Unit Price (PKR)" fill="#22d3ee" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Retail Price Distribution by Platform</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={retailData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
              <YAxis tick={axisTick} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Bar dataKey="List Price (PKR)" fill="#818cf8" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <motion.div className="grid grid-cols-1 gap-6 lg:grid-cols-2" variants={pageVariants}>
        <Card>
          <CardHeader>
            <CardTitle>Platform Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={platformData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#22d3ee"
                  dataKey="value"
                >
                  {platformData.map((_entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Price Range: Wholesale vs Retail</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priceRangeData}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend />
                <Bar dataKey="Min" fill="#22d3ee" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Avg" fill="#818cf8" radius={[8, 8, 0, 0]} />
                <Bar dataKey="Max" fill="#f59e0b" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle>Profit Potential by Supplier</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={profitData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
              <YAxis tick={axisTick} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Line
                type="monotone"
                dataKey="Profit Potential"
                stroke="#34d399"
                strokeWidth={2}
                dot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {wholesaleItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>MOQ vs Unit Price Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={wholesaleData}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
                <XAxis dataKey="name" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis yAxisId="left" tick={axisTick} axisLine={false} tickLine={false} />
                <YAxis yAxisId="right" orientation="right" tick={axisTick} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend />
                <Bar yAxisId="left" dataKey="Unit Price (PKR)" fill="#22d3ee" radius={[8, 8, 0, 0]} />
                <Bar yAxisId="right" dataKey="MOQ" fill="#818cf8" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
