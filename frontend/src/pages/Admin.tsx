import React, { useEffect, useState } from 'react';
import { adminAPI } from '../api/client';
import {
  Users,
  ShieldAlert,
  Database,
  BarChart3,
  Check,
  X,
  Plus,
  Trash2,
  Clock,
  AlertCircle,
  Loader2,
} from 'lucide-react';

export default function Admin() {
  const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'trusted' | 'logs'>('stats');
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [trusted, setTrusted] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // New trusted source form
  const [newDomain, setNewDomain] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newNotes, setNewNotes] = useState('');

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, trustedRes, logsRes] = await Promise.all([
        adminAPI.getStats(),
        adminAPI.getUsers(),
        adminAPI.getTrusted(),
        adminAPI.getLogs({ limit: 100 }),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data);
      setTrusted(trustedRes.data);
      setLogs(logsRes.data);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleUser = async (userId: number) => {
    try {
      await adminAPI.toggleUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: !u.is_active } : u))
      );
    } catch (err) {
      console.error('Toggle user failed:', err);
    }
  };

  const handleAddTrusted = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDomain.trim()) return;
    try {
      const res = await adminAPI.addTrusted({
        domain: newDomain.trim(),
        category: newCategory.trim() || undefined,
        notes: newNotes.trim() || undefined,
      });
      setTrusted((prev) => [...prev, res.data]);
      setNewDomain('');
      setNewCategory('');
      setNewNotes('');
    } catch (err) {
      console.error('Add trusted source failed:', err);
    }
  };

  const handleDeleteTrusted = async (sourceId: number) => {
    try {
      await adminAPI.deleteTrusted(sourceId);
      setTrusted((prev) => prev.filter((s) => s.id !== sourceId));
    } catch (err) {
      console.error('Delete trusted failed:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Admin & System Controls</h1>
        <p className="text-sm text-slate-500 mt-1">
          Manage system users, trusted scientific & news domains, view agent execution logs, and monitor performance.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-2">
        {[
          { key: 'stats', label: 'System Overview', icon: BarChart3 },
          { key: 'users', label: 'User Management', icon: Users },
          { key: 'trusted', label: 'Trusted Sources', icon: ShieldAlert },
          { key: 'logs', label: 'Agent Logs', icon: Database },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="py-20 text-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-xs text-slate-500">Loading system data...</p>
        </div>
      ) : (
        <>
          {/* TAB 1: System Overview */}
          {activeTab === 'stats' && stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Total Users</span>
                  <p className="text-2xl font-black text-slate-900 mt-1">{stats.total_users}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Requests Verified</span>
                  <p className="text-2xl font-black text-slate-900 mt-1">{stats.total_requests}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Total Claims</span>
                  <p className="text-2xl font-black text-slate-900 mt-1">{stats.total_claims}</p>
                </div>
                <div className="bg-white p-5 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Avg Agent Latency</span>
                  <p className="text-2xl font-black text-indigo-600 mt-1">{stats.avg_latency_ms} ms</p>
                </div>
              </div>

              {/* Label Breakdown */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 space-y-4">
                <h3 className="text-sm font-bold text-slate-900">Total Pipeline Label Breakdown</h3>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  {Object.entries(stats.label_distribution || {}).map(([lbl, count]: any) => (
                    <div key={lbl} className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <p className="text-[11px] font-bold text-slate-600">{lbl}</p>
                      <p className="text-xl font-black text-slate-900 mt-1">{count}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: User Management */}
          {activeTab === 'users' && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="p-3.5">ID</th>
                    <th className="p-3.5">Name</th>
                    <th className="p-3.5">Email</th>
                    <th className="p-3.5">Role</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="p-3.5 font-mono">#{u.id}</td>
                      <td className="p-3.5 font-bold text-slate-900">{u.name}</td>
                      <td className="p-3.5">{u.email}</td>
                      <td className="p-3.5 uppercase text-[10px] font-mono">{u.role}</td>
                      <td className="p-3.5">
                        <span
                          className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="p-3.5 text-right">
                        <button
                          onClick={() => handleToggleUser(u.id)}
                          className={`px-3 py-1 rounded-lg font-semibold text-[11px] transition-colors ${
                            u.is_active
                              ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                              : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: Trusted Sources */}
          {activeTab === 'trusted' && (
            <div className="space-y-6">
              {/* Add form */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Plus size={14} className="text-blue-500" />
                  <span>Add Trusted Domain</span>
                </h3>
                <form onSubmit={handleAddTrusted} className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <input
                    type="text"
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    placeholder="Domain (e.g. nature.com)"
                    className="text-xs border border-slate-200 rounded-xl px-3 py-2 text-slate-800"
                    required
                  />
                  <input
                    type="text"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    placeholder="Category (e.g. Scientific)"
                    className="text-xs border border-slate-200 rounded-xl px-3 py-2 text-slate-800"
                  />
                  <input
                    type="text"
                    value={newNotes}
                    onChange={(e) => setNewNotes(e.target.value)}
                    placeholder="Notes"
                    className="text-xs border border-slate-200 rounded-xl px-3 py-2 text-slate-800"
                  />
                  <button
                    type="submit"
                    className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl py-2 transition-colors"
                  >
                    Add Domain
                  </button>
                </form>
              </div>

              {/* Trusted sources list */}
              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                    <tr>
                      <th className="p-3.5">Domain</th>
                      <th className="p-3.5">Category</th>
                      <th className="p-3.5">Notes</th>
                      <th className="p-3.5 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {trusted.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-50">
                        <td className="p-3.5 font-bold text-slate-900">{s.domain}</td>
                        <td className="p-3.5">{s.category || 'General'}</td>
                        <td className="p-3.5 text-slate-500">{s.notes || '—'}</td>
                        <td className="p-3.5 text-right">
                          <button
                            onClick={() => handleDeleteTrusted(s.id)}
                            className="text-rose-600 hover:text-rose-800 p-1"
                            title="Remove domain"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: Agent Execution Logs */}
          {activeTab === 'logs' && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="p-3.5">Request</th>
                    <th className="p-3.5">Agent</th>
                    <th className="p-3.5">Latency</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="p-3.5 font-mono">#{log.request_id}</td>
                      <td className="p-3.5 font-bold text-slate-900">{log.agent_name}</td>
                      <td className="p-3.5 font-mono text-slate-600">{log.latency_ms ?? '—'} ms</td>
                      <td className="p-3.5">
                        {log.error ? (
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
                            Error
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Success
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 text-slate-500">{new Date(log.created_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
