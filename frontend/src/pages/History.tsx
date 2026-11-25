import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { historyAPI } from '../api/client';
import { VerificationRequest } from '../types';
import { Search, Filter, ArrowRight, Calendar, FileText, Loader2 } from 'lucide-react';

export default function History() {
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [selectedType, setSelectedType] = useState('');

  const loadHistory = async () => {
    setLoading(true);
    try {
      const res = await historyAPI.list({
        q: searchQuery.trim() || undefined,
        label: selectedLabel || undefined,
        input_type: selectedType || undefined,
      });
      setRequests(res.data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [selectedLabel, selectedType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadHistory();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Verification History</h1>
        <p className="text-sm text-slate-500 mt-1">
          Search and filter previously verified claims, articles, files, and URLs.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by claim text, keywords, or URL..."
              className="w-full text-xs border border-slate-200 rounded-xl pl-9 pr-3.5 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl shadow transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex gap-2">
          <select
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value)}
            className="text-xs border border-slate-200 rounded-xl px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Verdicts</option>
            <option value="Supported">Supported</option>
            <option value="Contradicted">Contradicted</option>
            <option value="Partially Supported">Partially Supported</option>
            <option value="Insufficient Evidence">Insufficient Evidence</option>
            <option value="Conflicting Evidence">Conflicting Evidence</option>
          </select>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="text-xs border border-slate-200 rounded-xl px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Input Types</option>
            <option value="claim">Claim</option>
            <option value="article">Article</option>
            <option value="file">File</option>
            <option value="url">URL</option>
          </select>
        </div>
      </div>

      {/* Requests Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
            <p className="text-xs text-slate-500">Loading history records...</p>
          </div>
        ) : requests.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {requests.map((r) => (
              <Link
                key={r.id}
                to={`/requests/${r.id}`}
                className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors block"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-mono text-xs font-bold shrink-0">
                    #{r.id}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 capitalize">
                        {r.input_type} Verification
                      </span>
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          r.status === 'done'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {r.claims_count} claim(s) extracted &bull;{' '}
                      <span className="inline-flex items-center gap-1">
                        <Calendar size={10} />
                        {new Date(r.created_at).toLocaleString()}
                      </span>
                    </p>
                    {r.source_url && (
                      <p className="text-[11px] text-blue-600 truncate max-w-md mt-0.5">
                        {r.source_url}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-semibold text-blue-600">
                  <span className="hidden sm:inline">View Results</span>
                  <ArrowRight size={14} />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="py-16 text-center text-xs text-slate-400">
            No verification records matching your filters.
          </div>
        )}
      </div>
    </div>
  );
}
