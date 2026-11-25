import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { verifyAPI } from '../api/client';
import { Globe, ShieldAlert, Loader2, AlertCircle } from 'lucide-react';

export default function VerifyUrl() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await verifyAPI.submitUrl({ url: url.trim() });
      navigate(`/requests/${res.data.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch and verify URL.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Verify Web URL</h1>
        <p className="text-sm text-slate-500 mt-1">
          Provide any public news article, blog, or online post URL. TruthLens securely fetches content with SSRF protection, extracts claims, and evaluates factual accuracy.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Article or Web Page URL
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Globe size={18} />
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/news/article"
                className="w-full text-sm border border-slate-200 rounded-xl pl-10 pr-3.5 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800"
                required
              />
            </div>
          </div>

          <div className="flex items-start gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px] text-slate-600">
            <ShieldAlert size={14} className="text-blue-500 shrink-0 mt-0.5" />
            <span>
              <b>SSRF & Security Protected:</b> Private, internal, loopback, and link-local IP addresses are strictly blocked.
            </span>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-rose-700 text-xs">
              <AlertCircle size={14} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl shadow-md transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Fetching Web Page & Running Pipeline...</span>
              </>
            ) : (
              <>
                <Globe size={16} />
                <span>Fetch & Verify URL</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
