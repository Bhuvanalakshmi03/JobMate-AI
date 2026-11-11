export type ResumeParseStatus = "uploaded" | "parsing" | "parsed" | "analyzed" | "failed";

export type FactType =
  | "personal_info"
  | "education"
  | "experience"
  | "internship"
  | "project"
  | "skill"
  | "certification"
  | "achievement";

export type VerificationStatus = "pending" | "verified" | "edited" | "rejected";
export type VerificationAction = "verify" | "edit" | "reject";

export interface ResumeSummary {
  id: string;
  original_filename: string;
  content_type: string;
  file_extension: string;
  file_size_bytes: number;
  page_count?: number | null;
  parse_status: ResumeParseStatus | string;
  completeness_score?: number | null;
  error_message?: string | null;
  analyzed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeListResponse {
  items: ResumeSummary[];
  total: number;
}

export interface ResumeAnalysisSummary {
  overall_assessment?: string;
  strengths?: string[];
  weaknesses?: string[];
  missing_skills?: string[];
  recommendations?: string[];
  model_used?: string;
  tokens_used?: number;
}

export interface ResumeFact {
  id: string;
  resume_id: string;
  fact_type: FactType | string;
  title: string;
  organization?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
  structured_data?: Record<string, unknown> | null;
  source_section?: string | null;
  evidence_excerpt?: string | null;
  confidence: number;
  verification_status: VerificationStatus | string;
  is_verified: boolean;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeAnalysisResponse {
  resume: ResumeSummary;
  completeness_score?: number | null;
  analysis_summary?: ResumeAnalysisSummary | null;
  facts: ResumeFact[];
}

export interface FactPatchItem {
  fact_id: string;
  action: VerificationAction;
  title?: string;
  organization?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  description?: string | null;
  structured_data?: Record<string, unknown> | null;
}

export interface ResumeFactsPatchResponse {
  facts: ResumeFact[];
  verified_count: number;
  synced_to_profile: boolean;
  synced_skills_count: number;
}
