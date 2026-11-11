import { apiRequest, getApiBaseUrl } from "./api-client";
import type {
  ExportFormat,
  GeneratedDocument,
  GeneratedDocumentDetail,
  GeneratedDocumentListResponse,
} from "../types/document";

export const documentService = {
  tailorResume: (params: {
    job_id: string;
    resume_id?: string | null;
    focus_instructions?: string | null;
  }): Promise<GeneratedDocument> =>
    apiRequest<GeneratedDocument>("/documents/tailor-resume", {
      method: "POST",
      timeoutMs: 60000,
      body: JSON.stringify(params),
    }),

  generateCoverLetter: (params: {
    job_id: string;
    resume_id?: string | null;
    tone?: "professional" | "enthusiastic" | "concise";
    custom_notes?: string | null;
  }): Promise<GeneratedDocument> =>
    apiRequest<GeneratedDocument>("/documents/cover-letter", {
      method: "POST",
      timeoutMs: 60000,
      body: JSON.stringify(params),
    }),

  generateApplicationNote: (params: {
    job_id: string;
    resume_id?: string | null;
    max_words?: number;
  }): Promise<GeneratedDocument> =>
    apiRequest<GeneratedDocument>("/documents/application-note", {
      method: "POST",
      timeoutMs: 45000,
      body: JSON.stringify(params),
    }),

  listDocuments: (jobId?: string): Promise<GeneratedDocumentListResponse> =>
    apiRequest<GeneratedDocumentListResponse>(
      jobId ? `/documents?job_id=${encodeURIComponent(jobId)}` : "/documents"
    ),

  getDocument: (documentId: string): Promise<GeneratedDocumentDetail> =>
    apiRequest<GeneratedDocumentDetail>(`/documents/${documentId}`),

  updateDocument: (
    documentId: string,
    payload: {
      title?: string;
      content_markdown?: string;
      create_new_version?: boolean;
    }
  ): Promise<GeneratedDocumentDetail> =>
    apiRequest<GeneratedDocumentDetail>(`/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getDownloadUrl: (documentId: string, format: ExportFormat): string =>
    `${getApiBaseUrl()}/documents/${documentId}/download?format=${format}`,
};
