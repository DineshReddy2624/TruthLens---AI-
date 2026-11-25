import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { verifyAPI } from '../api/client';
import VerdictBadge from '../components/VerdictBadge';
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  FileText,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        const res = await verifyAPI.getDashboardStats();
        setStats(res.data);
      } catch (err) {
        console.error('Failed to load dashboard stats:', err);
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const COLORS: Record<string, string> = {
    Supported: '#10b981',
    Contradicted: '#f43f5e',
    'Partially Supported': '#f59e0b',
    'Insufficient Evidence': '#64748b',
    'Conflicting Evidence': '#a855f7',
  };

  const chartData: { name: string; value: number }[] = stats?.label_distribution
    ? Object.entries(stats.label_distribution).map(([name, value]) => ({
        name,
        value: Number(value),
      }))
    : [];

  return (
    <div className="space-y-8">
      {/* Top Welcome / Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-blue-900 to-indigo-900 p-8 rounded-2xl text-white shadow-lg">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
            Fact-Verification Dashboard
          </h1>
          <p className="text-blue-200 text-sm mt-1 max-w-xl">
            Autonomous multi-agent verification pipeline synthesizing web retrieval, DeBERTa NLI, and cross-encoder reranking.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Link
            to="/verify/claim"
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 font-semibold text-xs rounded-xl shadow transition-colors flex items-center gap-1.5"
          >
            <CheckCircle size={14} />
            <span>Verify Claim</span>
          </Link>
          <Link
            to="/verify/file"
            className="px-4 py-2 bg-white/10 hover:bg-white/20 font-semibold text-xs rounded-xl backdrop-blur transition-colors flex items-center gap-1.5"
          >
            <FileText size={14} />
            <span>Upload Document</span>
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Claims</span>
            <ShieldCheck size={18} className="text-blue-500" />
          </div>
          <p className="text-3xl font-black text-slate-900">{stats?.total_claims || 0}</p>
          <p className="text-[11px] text-slate-500 mt-1">Across {stats?.total_requests || 0} verification requests</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Supported</span>
            <CheckCircle size={18} className="text-emerald-500" />
          </div>
          <p className="text-3xl font-black text-emerald-600">
            {stats?.label_distribution?.['Supported'] || 0}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Empirically confirmed factual claims</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Contradicted</span>
            <XCircle size={18} className="text-rose-500" />
          </div>
          <p className="text-3xl font-black text-rose-600">
            {stats?.label_distribution?.['Contradicted'] || 0}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Debunked myths & inaccuracies</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Avg Confidence</span>
            <TrendingUp size={18} className="text-indigo-500" />
          </div>
          <p className="text-3xl font-black text-indigo-600">
            {stats ? `${Math.round(stats.avg_confidence * 100)}%` : '0%'}
          </p>
          <p className="text-[11px] text-slate-500 mt-1">NLI agreement & source credibility</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pie / Donut Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span>Label Distribution Breakdown</span>
            <span className="text-xs font-normal text-slate-500">5 Strict Labels</span>
          </h2>
          <div className="h-64 flex items-center justify-center">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#64748b'} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-slate-400">No verification data yet.</p>
            )}
          </div>
          <div className="flex flex-wrap gap-3 justify-center text-xs mt-2">
            {chartData.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: COLORS[d.name] || '#64748b' }}
                />
                <span className="text-slate-600">{d.name} ({d.value})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bar Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-4 flex items-center justify-between">
            <span>Claim Verification Counts</span>
            <span className="text-xs font-normal text-slate-500">Aggregated Frequency</span>
          </h2>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} interval={0} angle={-15} textAnchor="end" />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={COLORS[entry.name] || '#64748b'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-xs text-slate-400">No verification data yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Activity List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Recent Verification Requests</h2>
          <Link to="/history" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
            <span>View All</span>
            <ArrowRight size={12} />
          </Link>
        </div>

        <div className="divide-y divide-slate-100">
          {stats?.recent_activity && stats.recent_activity.length > 0 ? (
            stats.recent_activity.map((req: any) => (
              <Link
                key={req.id}
                to={`/requests/${req.id}`}
                className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors block"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-mono text-xs font-bold">
                    #{req.id}
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-900 capitalize block">
                      {req.input_type} Verification
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {req.claims_count} claim(s) &bull; {new Date(req.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`text-[11px] font-semibold uppercase px-2.5 py-0.5 rounded-full ${
                      req.status === 'done'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : req.status === 'failed'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                  >
                    {req.status}
                  </span>
                  <ArrowRight size={14} className="text-slate-400" />
                </div>
              </Link>
            ))
          ) : (
            <div className="p-8 text-center text-xs text-slate-400">
              No recent requests found. Submit a claim to start fact-checking!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
