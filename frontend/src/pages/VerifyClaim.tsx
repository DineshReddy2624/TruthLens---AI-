import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { verifyAPI } from '../api/client';
import { CheckCircle, Sparkles, Loader2, AlertCircle } from 'lucide-react';

export default function VerifyClaim() {
  const [claimText, setClaimText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const exampleClaims = [
    'People say that the Great Wall of China is visible from space with the naked eye.',
    'Earth orbits around the Sun at an average orbital speed of roughly 30 km/s.',
    'The COVID-19 mRNA vaccines alter human DNA permanently.',
    'Drinking hot water with lemon cures coronavirus infections.',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claimText.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await verifyAPI.submitText({
        text: claimText.trim(),
        input_type: 'claim',
      });
      navigate(`/requests/${res.data.id}`);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to submit claim for verification.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Verify a Claim</h1>
        <p className="text-sm text-slate-500 mt-1">
          Submit any single factual statement. TruthLens will retrieve opposing viewpoints, cross-reference credible sources, and compute an objective verdict.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Factual Claim Statement
            </label>
            <textarea
              rows={4}
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              placeholder="e.g. The Great Wall of China is visible from space with the unaided eye."
              className="w-full text-sm border border-slate-200 rounded-xl p-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800"
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
            disabled={loading || !claimText.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold text-sm rounded-xl shadow-md transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Running Verification Pipeline (Search, NLI, Credibility)...</span>
              </>
            ) : (
              <>
                <CheckCircle size={16} />
                <span>Verify Claim</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Examples */}
      <div className="bg-slate-50 p-5 rounded-2xl border border-slate-200">
        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 uppercase tracking-wider mb-3">
          <Sparkles size={14} className="text-blue-500" />
          <span>Quick Examples to Try</span>
        </div>
        <div className="space-y-2">
          {exampleClaims.map((claim, idx) => (
            <button
              key={idx}
              onClick={() => setClaimText(claim)}
              className="w-full text-left p-3 rounded-xl bg-white border border-slate-200 text-xs text-slate-700 hover:border-blue-400 hover:text-blue-600 transition-colors shadow-2xs"
            >
              "{claim}"
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
