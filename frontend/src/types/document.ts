export type DocumentType = "tailored_resume" | "cover_letter" | "application_note";
export type ExportFormat = "pdf" | "docx" | "md";

export interface FactualityReport {
  is_grounded: boolean;
  verified_fact_ids: string[];
  checked_claims_count: number;
  unsupported_claims: string[];
}

export interface DocumentVersionSummary {
  id: string;
  version: number;
  is_user_edited: boolean;
  created_at: string;
}

export interface GeneratedDocument {
  id: string;
  user_id: string;
  job_id?: string | null;
  source_resume_id?: string | null;
  document_type: DocumentType | string;
  title: string;
  version_group_id: string;
  version: number;
  content_markdown: string;
  structured_content?: Record<string, unknown> | null;
  factuality_report: FactualityReport;
  is_user_edited: boolean;
  model_used?: string | null;
  tokens_used?: number | null;
  created_at: string;
  updated_at: string;
}

export interface GeneratedDocumentDetail extends GeneratedDocument {
  versions: DocumentVersionSummary[];
}

export interface GeneratedDocumentListResponse {
  items: GeneratedDocument[];
  total: number;
}
