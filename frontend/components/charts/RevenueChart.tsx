'use client';

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface RevenueChartProps {
  data: Array<{ month: string; revenue: number; projected?: boolean }>;
  className?: string;
}

export function RevenueChart({ data, className = '' }: RevenueChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
          <defs>
            <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3182ce" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3182ce" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="month"
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `$${(v / 100).toLocaleString()}`}
          />
          <Tooltip
            contentStyle={{
              background: '#0f1720',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              color: '#e2e8f0',
              fontSize: 12,
            }}
            formatter={(v: number) => [`$${(v / 100).toLocaleString()}`, 'Revenue']}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#3182ce"
            strokeWidth={2}
            fill="url(#revGrad)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

interface AgingChartProps {
  data: Array<{ label: string; total_cents: number; count: number }>;
  className?: string;
}

const AGING_COLORS = ['#48bb78', '#68d391', '#f6ad55', '#f6874a', '#fc6b52'];

export function AgingChart({ data, className = '' }: AgingChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="label"
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `$${(v / 100 / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{
              background: '#0f1720',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              color: '#e2e8f0',
              fontSize: 12,
            }}
            formatter={(v: number, _: string, props: { payload?: { count: number } }) => [
              `$${(v / 100).toLocaleString()} (${props.payload?.count ?? 0} claims)`,
              'AR Balance',
            ]}
          />
          <Bar dataKey="total_cents" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={AGING_COLORS[i % AGING_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
