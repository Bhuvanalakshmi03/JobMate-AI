import { FileText, Sparkles, Trash2, Upload } from "lucide-react";
import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  useAnalyzeResumeMutation,
  useDeleteResumeMutation,
  useResumesList,
  useUploadResumeMutation,
} from "../hooks/useResumes";

const MAX_SIZE_BYTES = 5 * 1024 * 1024;

function parseTone(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "analyzed") return "success";
  if (status === "parsed") return "info";
  if (status === "failed") return "danger";
  return "warning";
}

export function ResumesPage() {
  const listQuery = useResumesList();
  const uploadMutation = useUploadResumeMutation();
  const analyzeMutation = useAnalyzeResumeMutation();
  const deleteMutation = useDeleteResumeMutation();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setValidationError(null);
    const file = e.target.files?.[0] ?? null;
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const lowered = file.name.toLowerCase();
    if (!lowered.endsWith(".pdf") && !lowered.endsWith(".docx")) {
      setValidationError("Only PDF (.pdf) and Word (.docx) resumes are supported.");
      setSelectedFile(null);
      return;
    }
    if (file.size === 0) {
      setValidationError("Selected file is empty.");
      setSelectedFile(null);
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setValidationError("Resume exceeds maximum allowed size of 5 MB.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setValidationError("Select a PDF or DOCX resume before uploading.");
      return;
    }
    setValidationError(null);
    await uploadMutation.mutateAsync(selectedFile);
    setSelectedFile(null);
  };

  const handleAnalyze = async (resumeId: string) => {
    setAnalyzingId(resumeId);
    try {
      await analyzeMutation.mutateAsync({ resumeId });
    } finally {
      setAnalyzingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Resume Intelligence</h1>
        <p className="mt-1 text-sm text-slate-600">
          Upload your PDF or DOCX resume for structured extraction, quality feedback, and
          human-verified profile syncing. Originals are stored privately and never overwritten.
        </p>
      </header>

      <Card
        title="Upload Resume"
        subtitle="Supported formats: PDF and DOCX up to 5 MB (max 15 pages)."
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input
            aria-label="Resume file"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleFileChange}
            className="block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border file:border-slate-300 file:bg-white file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-50"
          />
          <button
            type="button"
            disabled={uploadMutation.isPending || !selectedFile}
            onClick={() => void handleUpload()}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            {uploadMutation.isPending ? "Uploading..." : "Upload Resume"}
          </button>
        </div>

        {validationError && (
          <div className="mt-3">
            <StateNotice title="Invalid file" description={validationError} tone="error" />
          </div>
        )}

        {uploadMutation.error && (
          <div className="mt-3">
            <StateNotice
              title="Upload failed"
              description={uploadMutation.error.message}
              tone="error"
            />
          </div>
        )}

        {uploadMutation.isSuccess && !uploadMutation.error && (
          <div className="mt-3">
            <StateNotice
              title="Resume uploaded and parsed"
              description="Click Analyze with AI below to extract verifiable career facts."
              tone="info"
            />
          </div>
        )}
      </Card>

      <Card title="Uploaded Resumes" subtitle="Verify extracted facts before syncing to your profile.">
        {listQuery.isPending && (
          <StateNotice
            title="Loading resumes..."
            description="Fetching your uploaded resume vault."
            tone="info"
          />
        )}

        {listQuery.error && (
          <StateNotice
            title="Unable to load resumes"
            description={listQuery.error.message}
            tone="error"
          />
        )}

        {analyzeMutation.error && (
          <div className="mb-4">
            <StateNotice
              title="AI resume analysis failed"
              description={analyzeMutation.error.message}
              tone="error"
            />
          </div>
        )}

        {!listQuery.isPending && !listQuery.error && listQuery.data?.items.length === 0 && (
          <StateNotice
            title="No resumes uploaded yet"
            description="Upload a PDF or DOCX resume above to start AI analysis and fact verification."
            tone="empty"
          />
        )}

        {!listQuery.isPending && !listQuery.error && (listQuery.data?.items.length ?? 0) > 0 && (
          <ul className="divide-y divide-slate-200">
            {listQuery.data!.items.map((resume) => (
              <li
                key={resume.id}
                className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600">
                    <FileText className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-slate-900">
                        {resume.original_filename}
                      </p>
                      <StatusBadge
                        label={resume.parse_status.toUpperCase()}
                        tone={parseTone(resume.parse_status)}
                      />
                      {resume.completeness_score != null && (
                        <StatusBadge
                          label={`${Math.round(resume.completeness_score)}% complete`}
                          tone="info"
                        />
                      )}
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      {resume.file_extension.toUpperCase()} ·{" "}
                      {(resume.file_size_bytes / 1024).toFixed(1)} KB
                      {resume.page_count ? ` · ${resume.page_count} page(s)` : ""}
                    </p>
                    {resume.error_message && (
                      <p className="mt-1 text-xs text-rose-600">{resume.error_message}</p>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={analyzingId === resume.id}
                    onClick={() => void handleAnalyze(resume.id)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                    {analyzingId === resume.id
                      ? "Analyzing..."
                      : resume.parse_status === "analyzed"
                        ? "View Analysis"
                        : "Analyze with AI"}
                  </button>
                  <Link
                    to={`/resumes/${resume.id}`}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Review Facts
                  </Link>
                  <button
                    type="button"
                    aria-label={`Delete ${resume.original_filename}`}
                    disabled={deleteMutation.isPending}
                    onClick={() => void deleteMutation.mutateAsync(resume.id)}
                    className="rounded-lg border border-rose-200 bg-rose-50 p-1.5 text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
