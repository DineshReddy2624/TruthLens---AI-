import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { verifyAPI } from '../api/client';
import { FileText, Loader2, AlertCircle } from 'lucide-react';

export default function VerifyArticle() {
  const [articleText, setArticleText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!articleText.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await verifyAPI.submitText({
        text: articleText.trim(),
        input_type: 'article',
      });
      navigate(`/requests/${res.data.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to submit article for verification.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Verify an Article</h1>
        <p className="text-sm text-slate-500 mt-1">
          Paste a full-length article, blog post, or editorial text. The Claim Extraction Agent will decompose it into individual checkable claims.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Article Content
            </label>
            <textarea
              rows={12}
              value={articleText}
              onChange={(e) => setArticleText(e.target.value)}
              placeholder="Paste article text here... (TruthLens will extract all factual claims and verify each independently)"
              className="w-full text-sm border border-slate-200 rounded-xl p-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 font-sans"
              required
            />
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-rose-700 text-xs">
              <AlertCircle size={14} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !articleText.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl shadow-md transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Extracting Claims & Verifying Evidence...</span>
              </>
            ) : (
              <>
                <FileText size={16} />
                <span>Extract & Verify Article Claims</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
