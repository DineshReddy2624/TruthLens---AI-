import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { verifyAPI, ragAPI, reportsAPI } from '../api/client';
import { VerificationDetail as IVerificationDetail, ExtractedClaim, ChatMessage } from '../types';
import VerdictBadge from '../components/VerdictBadge';
import ConfidenceMeter from '../components/ConfidenceMeter';
import EvidenceCard from '../components/EvidenceCard';
import {
  Download,
  Loader2,
  AlertTriangle,
  Send,
  MessageSquare,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  Layers,
  Clock,
  Tag,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from 'lucide-react';

export default function VerificationDetail() {
  const { id } = useParams<{ id: string }>();
  const requestId = parseInt(id || '0', 10);

  const [request, setRequest] = useState<IVerificationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedClaimIdx, setSelectedClaimIdx] = useState(0);
  const [highlightedPassageId, setHighlightedPassageId] = useState<number | null>(null);

  // RAG Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [userQuery, setUserQuery] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [pdfGenerating, setPdfGenerating] = useState(false);

  useEffect(() => {
    async function loadData() {
      if (!requestId) return;
      try {
        const res = await verifyAPI.getVerification(requestId);
        setRequest(res.data);

        // Load chat history
        const chatRes = await ragAPI.getHistory(requestId);
        setChatMessages(chatRes.data);
      } catch (err) {
        console.error('Failed to load verification:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [requestId]);

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userQuery.trim() || chatLoading || !requestId) return;

    const query = userQuery.trim();
    setUserQuery('');
    setChatLoading(true);

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      role: 'user',
      message: query,
      created_at: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await ragAPI.chat(requestId, query);
      const asstMsg: ChatMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        message: res.data.answer,
        citations: res.data.citations_metadata,
        created_at: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, asstMsg]);
    } catch (err) {
      console.error('RAG chat failed:', err);
    } finally {
      setChatLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!requestId) return;
    setPdfGenerating(true);
    try {
      await reportsAPI.generate(requestId);
      const res = await reportsAPI.download(requestId);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `TruthLens_Report_${requestId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF generation error, trying direct URL fallback:', err);
      window.open(reportsAPI.downloadUrl(requestId), '_blank');
    } finally {
      setPdfGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-4">
        <Loader2 className="w-10 h-10 animate-spin text-blue-600 mx-auto" />
        <p className="text-sm font-semibold text-slate-600">Loading Fact-Verification Results...</p>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="card text-center py-16">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-900">Verification Request Not Found</h2>
        <Link to="/dashboard" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const claims = request.claims || [];
  const currentClaim: ExtractedClaim | undefined = claims[selectedClaimIdx];
  const result = currentClaim?.result;

  // Separate evidence into Supporting, Contradicting, and Neutral
  const supportingEvidence = (currentClaim?.evidence_records || []).filter(
    (e) => (e.nli_label || '').toLowerCase() === 'entailment'
  );
  const contradictingEvidence = (currentClaim?.evidence_records || []).filter(
    (e) => (e.nli_label || '').toLowerCase() === 'contradiction'
  );
  const otherEvidence = (currentClaim?.evidence_records || []).filter(
    (e) =>
      (e.nli_label || '').toLowerCase() !== 'entailment' &&
      (e.nli_label || '').toLowerCase() !== 'contradiction'
  );

  // Helper to map source by source_id
  const getSource = (sourceId: number) => {
    return currentClaim?.sources.find((s) => s.id === sourceId);
  };

  // Render clickable citations [1][2] in explanation
  const renderExplanationWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const citNum = parseInt(match[1], 10);
        // Find evidence matching this index in currentClaim
        const targetEv = currentClaim?.evidence_records[citNum - 1];
        return (
          <button
            key={i}
            onClick={() => targetEv && setHighlightedPassageId(targetEv.id)}
            className="inline-flex items-center justify-center font-bold text-blue-600 hover:text-white hover:bg-blue-600 bg-blue-50 border border-blue-200 px-1.5 py-0.2 rounded text-[11px] mx-0.5 transition-colors cursor-pointer"
            title={`View evidence source [${citNum}]`}
          >
            {part}
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="space-y-8">
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
              #{request.id}
            </span>
            <span className="text-xs uppercase font-semibold text-slate-500">
              {request.input_type} Verification
            </span>
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                request.status === 'done'
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-amber-50 text-amber-700 border border-amber-200'
              }`}
            >
              {request.status}
            </span>
          </div>

          <p className="text-xs text-slate-500">
            Processed {claims.length} claim(s) &bull; Submitted {new Date(request.created_at).toLocaleString()}
          </p>
          {request.source_url && (
            <a
              href={request.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1 mt-1"
            >
              <span>{request.source_url}</span>
              <ExternalLink size={12} />
            </a>
          )}
        </div>

        <button
          onClick={handleDownloadPdf}
          disabled={pdfGenerating}
          className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-xl shadow transition-colors flex items-center justify-center gap-2 shrink-0"
        >
          {pdfGenerating ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Download size={14} />
          )}
          <span>Download PDF Fact-Check Report</span>
        </button>
      </div>

      {/* Claim Selector Tabs (if multiple claims) */}
      {claims.length > 1 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200">
          {claims.map((c, idx) => (
            <button
              key={c.id}
              onClick={() => {
                setSelectedClaimIdx(idx);
                setHighlightedPassageId(null);
              }}
              className={`px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-2 ${
                selectedClaimIdx === idx
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span>Claim #{idx + 1}</span>
              {c.result && <VerdictBadge label={c.result.label} size="sm" />}
            </button>
          ))}
        </div>
      )}

      {currentClaim ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Claim Detail Column (2 spans) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Standalone Claim Box */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="font-bold uppercase tracking-wider">Target Factual Claim</span>
                <span className="font-mono">Claim ID: {currentClaim.id}</span>
              </div>
              <h2 className="text-lg md:text-xl font-black text-slate-900 leading-snug">
                "{currentClaim.claim_text}"
              </h2>

              {/* Extracted Entities */}
              {currentClaim.entities && currentClaim.entities.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100">
                  <span className="text-[11px] font-semibold text-slate-400 mr-1 flex items-center gap-1">
                    <Tag size={11} /> Entities:
                  </span>
                  {currentClaim.entities.map((e, idx) => (
                    <span
                      key={idx}
                      className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200"
                    >
                      <b>{e.name}</b> <span className="text-[10px] text-slate-400">({e.category})</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Verdict & Confidence Banner */}
            {result ? (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div>
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                      Final Verified Verdict
                    </span>
                    <VerdictBadge label={result.label} size="lg" />
                  </div>

                  <div className="w-full sm:w-48">
                    <ConfidenceMeter confidence={result.confidence} />
                  </div>
                </div>

                {/* AI Explanation with Interactive Citations */}
                {result.explanation && (
                  <div>
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Sparkles size={14} className="text-blue-500" />
                      <span>Synthesized AI Explanation</span>
                    </h3>
                    <p className="text-sm text-slate-700 leading-relaxed bg-blue-50/40 p-4 rounded-xl border border-blue-100">
                      {renderExplanationWithCitations(result.explanation)}
                    </p>
                  </div>
                )}

                {/* Missing Context Alert */}
                {result.missing_context && (
                  <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2.5">
                    <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold block">Important Missing Context:</span>
                      <span>{result.missing_context}</span>
                    </div>
                  </div>
                )}

                {/* Contradictions Breakdown */}
                {result.conflicts && Object.keys(result.conflicts).length > 0 && (
                  <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-900 space-y-1.5">
                    <div className="flex items-center gap-1.5 font-bold">
                      <ShieldAlert size={15} className="text-purple-600" />
                      <span>Contradictions & Conflicting Evidence Found</span>
                    </div>
                    <p className="text-purple-800 leading-relaxed">
                      {result.conflicts.conflict_explanation || JSON.stringify(result.conflicts)}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200 text-center text-xs text-slate-500">
                Verification results pending or processing...
              </div>
            )}

            {/* Side-by-Side Supporting vs Contradicting Evidence */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Layers size={16} className="text-blue-500" />
                <span>Supporting vs. Contradicting Evidence Passages</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Supporting Column */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 size={14} />
                      <span>Supporting Evidence ({supportingEvidence.length})</span>
                    </div>
                    <span className="text-[10px] uppercase font-mono">Entailment</span>
                  </div>

                  {supportingEvidence.length > 0 ? (
                    supportingEvidence.map((ev) => (
                      <EvidenceCard
                        key={ev.id}
                        evidence={ev}
                        source={getSource(ev.source_id)}
                        highlighted={highlightedPassageId === ev.id}
                      />
                    ))
                  ) : (
                    <div className="p-6 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
                      No supporting passages retrieved.
                    </div>
                  )}
                </div>

                {/* Contradicting Column */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs font-bold text-rose-700 bg-rose-50 px-3 py-2 rounded-lg border border-rose-200">
                    <div className="flex items-center gap-1.5">
                      <XCircle size={14} />
                      <span>Contradicting Evidence ({contradictingEvidence.length})</span>
                    </div>
                    <span className="text-[10px] uppercase font-mono">Contradiction</span>
                  </div>

                  {contradictingEvidence.length > 0 ? (
                    contradictingEvidence.map((ev) => (
                      <EvidenceCard
                        key={ev.id}
                        evidence={ev}
                        source={getSource(ev.source_id)}
                        highlighted={highlightedPassageId === ev.id}
                      />
                    ))
                  ) : (
                    <div className="p-6 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
                      No contradicting passages retrieved.
                    </div>
                  )}
                </div>
              </div>

              {/* Contextual / Neutral Evidence */}
              {otherEvidence.length > 0 && (
                <div className="mt-4 space-y-3">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 bg-slate-100 px-3 py-2 rounded-lg">
                    <HelpCircle size={14} />
                    <span>Neutral & Background Passages ({otherEvidence.length})</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {otherEvidence.map((ev) => (
                      <EvidenceCard
                        key={ev.id}
                        evidence={ev}
                        source={getSource(ev.source_id)}
                        highlighted={highlightedPassageId === ev.id}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Sidebar: Claim Analysis & RAG Assistant (1 span) */}
          <div className="space-y-6">
            {/* Claim Analysis Card */}
            {currentClaim.analysis && (
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock size={14} className="text-blue-500" />
                  <span>Claim Analytical Dimensions</span>
                </h3>

                <div className="text-xs space-y-2 text-slate-600">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Claim Type:</span>
                    <b className="text-slate-800 capitalize">{currentClaim.analysis.claim_type}</b>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Topic:</span>
                    <b className="text-slate-800">{currentClaim.analysis.topic}</b>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Time Sensitive:</span>
                    <b className="text-slate-800">{currentClaim.analysis.is_time_sensitive ? 'Yes' : 'No'}</b>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span>Checkable:</span>
                    <b className="text-slate-800">{currentClaim.analysis.is_checkable ? 'Yes' : 'No'}</b>
                  </div>
                </div>

                {currentClaim.analysis.support_criteria && (
                  <div className="text-[11px] pt-1 text-slate-500">
                    <b>Support Criteria:</b> {currentClaim.analysis.support_criteria}
                  </div>
                )}
              </div>
            )}

            {/* RAG Assistant Interactive Chat Box */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col h-[520px]">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center">
                    <MessageSquare size={14} />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-900">RAG Research Assistant</h3>
                    <p className="text-[10px] text-slate-400">Ask questions with evidence citations</p>
                  </div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {chatMessages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 p-4">
                    <MessageSquare size={24} className="mb-2 text-slate-300" />
                    <p className="text-xs font-medium text-slate-600">Have questions about this article?</p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Ask about specific quotes, metrics, or sources. Answers will strictly cite retrieved evidence.
                    </p>
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col text-xs leading-relaxed ${
                        msg.role === 'user' ? 'items-end' : 'items-start'
                      }`}
                    >
                      <div
                        className={`p-3 rounded-xl max-w-[90%] ${
                          msg.role === 'user'
                            ? 'bg-blue-600 text-white rounded-br-none'
                            : 'bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200'
                        }`}
                      >
                        {msg.message}
                      </div>

                      {/* Assistant Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1 max-w-[90%]">
                          {msg.citations.map((c, idx) => (
                            <a
                              key={idx}
                              href={c.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] font-mono text-blue-600 hover:underline bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded"
                            >
                              [{c.citation_number}] {c.source_title || 'Source'}
                            </a>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex items-center gap-2 text-xs text-slate-400 p-2">
                    <Loader2 size={12} className="animate-spin text-blue-500" />
                    <span>Searching verified evidence passages...</span>
                  </div>
                )}
              </div>

              {/* Chat Input */}
              <form onSubmit={handleSendChat} className="p-3 border-t border-slate-100 flex gap-2">
                <input
                  type="text"
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.target.value)}
                  placeholder="Ask a question about this content..."
                  className="flex-1 text-xs border border-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                />
                <button
                  type="submit"
                  disabled={chatLoading || !userQuery.trim()}
                  className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white rounded-xl transition-colors"
                >
                  <Send size={14} />
                </button>
              </form>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
