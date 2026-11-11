import { Download, FileCheck2, Sparkles } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { documentService } from "../../../services/document-service";
import type { DocumentType } from "../../../types/document";
import { useJobSearch } from "../../jobs/hooks/useJobs";
import { useResumesList } from "../../resume/hooks/useResumes";
import { useDocumentsList, useGenerateDocumentMutation } from "../hooks/useDocuments";

export function DocumentsPage() {
  const [searchParams] = useSearchParams();
  const initialJobId = searchParams.get("jobId") ?? "";
  const navigate = useNavigate();

  const jobsQuery = useJobSearch({ limit: 30 }, true);
  const resumesQuery = useResumesList();
  const docsQuery = useDocumentsList();
  const generateMutation = useGenerateDocumentMutation();

  const [jobId, setJobId] = useState(initialJobId);
  const [resumeId, setResumeId] = useState("");
  const [kind, setKind] = useState<DocumentType>("tailored_resume");
  const [tone, setTone] = useState<"professional" | "enthusiastic" | "concise">("professional");
  const [instructions, setInstructions] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId && jobsQuery.data?.items.length) {
      setJobId(jobsQuery.data.items[0].id);
    }
  }, [jobId, jobsQuery.data]);

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    if (!jobId) {
      setValidationError("Select a target job listing before generating a document.");
      return;
    }
    setValidationError(null);
    const created = await generateMutation.mutateAsync({
      kind,
      jobId,
      resumeId: resumeId || null,
      instructions: instructions.trim() || null,
      tone,
    });
    navigate(`/documents/${created.id}`);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Document Studio</h1>
        <p className="mt-1 text-sm text-slate-600">
          Generate job-specific tailored resumes, cover letters, and application notes strictly from
          your verified career facts. Original resumes are never modified.
        </p>
      </header>

      <Card
        title="Generate Tailored Document"
        subtitle="Select a discovered job and optional verified source resume."
      >
        <form onSubmit={handleGenerate} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label htmlFor="doc-kind" className="block text-xs font-medium text-slate-700">
                Document type
              </label>
              <select
                id="doc-kind"
                value={kind}
                onChange={(e) => setKind(e.target.value as DocumentType)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="tailored_resume">Tailored Resume</option>
                <option value="cover_letter">Cover Letter</option>
                <option value="application_note">Application Note</option>
              </select>
            </div>

            <div>
              <label htmlFor="doc-job" className="block text-xs font-medium text-slate-700">
                Target job
              </label>
              <select
                id="doc-job"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="">Select a job...</option>
                {jobsQuery.data?.items.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title} — {job.company}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="doc-resume" className="block text-xs font-medium text-slate-700">
                Source resume (optional)
              </label>
              <select
                id="doc-resume"
                value={resumeId}
                onChange={(e) => setResumeId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              >
                <option value="">All verified facts & profile</option>
                {resumesQuery.data?.items.map((res) => (
                  <option key={res.id} value={res.id}>
                    {res.original_filename}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {kind === "cover_letter" && (
            <div className="sm:w-64">
              <label htmlFor="doc-tone" className="block text-xs font-medium text-slate-700">
                Cover letter tone
              </label>
              <select
                id="doc-tone"
                value={tone}
                onChange={(e) =>
                  setTone(e.target.value as "professional" | "enthusiastic" | "concise")
                }
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="professional">Professional</option>
                <option value="enthusiastic">Enthusiastic</option>
                <option value="concise">Concise</option>
              </select>
            </div>
          )}

          {kind !== "application_note" && (
            <div>
              <label htmlFor="doc-notes" className="block text-xs font-medium text-slate-700">
                Focus instructions (optional)
              </label>
              <input
                id="doc-notes"
                type="text"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="e.g. Emphasize backend APIs and database indexing projects"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
            </div>
          )}

          {validationError && (
            <StateNotice title="Missing selection" description={validationError} tone="error" />
          )}

          {generateMutation.error && (
            <StateNotice
              title="Document generation blocked"
              description={generateMutation.error.message}
              tone="error"
            />
          )}

          <button
            type="submit"
            disabled={generateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {generateMutation.isPending ? "Generating..." : "Generate Document"}
          </button>
        </form>
      </Card>

      <Card title="Generated Documents" subtitle="Edit, compare versions, and export PDF or DOCX.">
        {docsQuery.isPending && (
          <StateNotice
            title="Loading documents..."
            description="Fetching your tailored resumes and cover letters."
            tone="info"
          />
        )}

        {docsQuery.error && (
          <StateNotice
            title="Unable to load documents"
            description={docsQuery.error.message}
            tone="error"
          />
        )}

        {!docsQuery.isPending && !docsQuery.error && docsQuery.data?.items.length === 0 && (
          <StateNotice
            title="No generated documents yet"
            description="Choose a target job above to create a factually grounded tailored resume, cover letter, or short note."
            tone="empty"
          />
        )}

        {!docsQuery.isPending && !docsQuery.error && (docsQuery.data?.items.length ?? 0) > 0 && (
          <ul className="divide-y divide-slate-200">
            {docsQuery.data!.items.map((doc) => (
              <li
                key={doc.id}
                className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/documents/${doc.id}`}
                      className="text-sm font-semibold text-slate-900 hover:text-indigo-600"
                    >
                      {doc.title}
                    </Link>
                    <StatusBadge label={`v${doc.version}`} tone="info" />
                    <StatusBadge label={doc.document_type.replace("_", " ")} tone="neutral" />
                    {doc.factuality_report?.is_grounded && (
                      <StatusBadge label="Factually Grounded" tone="success" />
                    )}
                    {doc.is_user_edited && <StatusBadge label="Edited" tone="warning" />}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    to={`/documents/${doc.id}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    <FileCheck2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Preview & Edit
                  </Link>
                  <a
                    href={documentService.getDownloadUrl(doc.id, "pdf")}
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden="true" />
                    PDF
                  </a>
                  <a
                    href={documentService.getDownloadUrl(doc.id, "docx")}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    DOCX
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
