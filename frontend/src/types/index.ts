export type VerdictLabelType =
  | 'Supported'
  | 'Contradicted'
  | 'Partially Supported'
  | 'Insufficient Evidence'
  | 'Conflicting Evidence';

export interface SourceEvaluation {
  id: number;
  source_id: number;
  publisher_score: number;
  date_score: number;
  quality_score: number;
  corroboration_score: number;
  total_score: number;
  reason?: string;
}

export interface RetrievedSource {
  id: number;
  url: string;
  domain?: string;
  title?: string;
  publisher?: string;
  published_at?: string;
  evaluation?: SourceEvaluation;
}

export interface EvidenceRecord {
  id: number;
  source_id: number;
  passage: string;
  nli_label?: string;
  nli_scores?: Record<string, number>;
  rank_score?: number;
}

export interface VerificationResult {
  id: number;
  label: VerdictLabelType;
  confidence: number;
  key_passage_ids?: number[];
  missing_context?: string;
  conflicts?: Record<string, any>;
  explanation?: string;
  created_at: string;
}

export interface ExtractedEntity {
  name: string;
  category: string;
}

export interface ClaimAnalysis {
  claim_type: string;
  topic: string;
  is_time_sensitive: boolean;
  time_context?: string;
  support_criteria?: string;
  contradict_criteria?: string;
  is_checkable: boolean;
  uncheckable_reason?: string;
}

export interface ExtractedClaim {
  id: number;
  claim_text: string;
  claim_type?: string;
  entities?: ExtractedEntity[];
  analysis?: ClaimAnalysis;
  result?: VerificationResult;
  sources: RetrievedSource[];
  evidence_records: EvidenceRecord[];
  created_at: string;
}

export interface VerificationRequest {
  id: number;
  user_id: number;
  input_type: 'claim' | 'article' | 'file' | 'url';
  status: 'pending' | 'running' | 'done' | 'failed';
  source_url?: string;
  claims_count: number;
  created_at: string;
  updated_at: string;
}

export interface VerificationDetail extends VerificationRequest {
  raw_text_preview?: string;
  claims: ExtractedClaim[];
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  message: string;
  citations?: Array<{
    citation_number: number;
    evidence_id: number;
    source_url?: string;
    source_title?: string;
    passage: string;
  }>;
  created_at: string;
}
