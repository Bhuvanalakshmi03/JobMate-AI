import { ArrowLeft, Copy, Download, Save } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { documentService } from "../../../services/document-service";
import { useDocumentDetail, useUpdateDocumentMutation } from "../hooks/useDocuments";

export function DocumentEditorPage() {
  const { documentId = "" } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const detailQuery = useDocumentDetail(documentId);
  const updateMutation = useUpdateDocumentMutation(documentId);

  const [title, setTitle] = useState("");
  const [contentMarkdown, setContentMarkdown] = useState("");
  const [createNewVersion, setCreateNewVersion] = useState(true);
  const [copied, setCopied] = useState(false);

  const doc = detailQuery.data;

  useEffect(() => {
    if (doc) {
      setTitle(doc.title);
      setContentMarkdown(doc.content_markdown);
    }
  }, [doc]);

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !contentMarkdown.trim()) return;
    const saved = await updateMutation.mutateAsync({
      title: title.trim(),
      content_markdown: contentMarkdown,
      create_new_version: createNewVersion,
    });
    if (saved.id !== documentId) {
      navigate(`/documents/${saved.id}`, { replace: true });
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard?.writeText(contentMarkdown);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            to="/documents"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            Back to Document Studio
          </Link>
          <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">
            {doc?.title ?? "Document Preview & Editor"}
          </h1>
        </div>

        {doc && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void handleCopy()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
              {copied ? "Copied" : "Copy"}
            </button>
            <a
              href={documentService.getDownloadUrl(doc.id, "pdf")}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              Export PDF
            </a>
            <a
              href={documentService.getDownloadUrl(doc.id, "docx")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              Export DOCX
            </a>
          </div>
        )}
      </div>

      {detailQuery.isPending && (
        <StateNotice
          title="Loading document..."
          description="Fetching content, factuality audit, and version history."
          tone="info"
        />
      )}

      {detailQuery.error && (
        <StateNotice
          title="Unable to load document"
          description={detailQuery.error.message}
          tone="error"
        />
      )}

      {doc && (
        <div className="grid gap-6 lg:grid-cols-3">
          <form onSubmit={handleSave} className="space-y-4 lg:col-span-2">
            <Card
              title="Editable Content"
              subtitle={`Version v${doc.version} · ${doc.document_type.replace("_", " ")}`}
              action={
                doc.factuality_report?.is_grounded ? (
                  <StatusBadge label="Verified Facts Grounded" tone="success" />
                ) : null
              }
            >
              <div className="space-y-4">
                <div>
                  <label htmlFor="edit-doc-title" className="block text-xs font-medium text-slate-700">
                    Document title
                  </label>
                  <input
                    id="edit-doc-title"
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label
                    htmlFor="edit-doc-content"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Content (Markdown / ATS plain layout)
                  </label>
                  <textarea
                    id="edit-doc-content"
                    rows={18}
                    required
                    value={contentMarkdown}
                    onChange={(e) => setContentMarkdown(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs leading-relaxed focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={createNewVersion}
                      onChange={(e) => setCreateNewVersion(e.target.checked)}
                    />
                    Save as new version (preserve v{doc.version})
                  </label>
                  <button
                    type="submit"
                    disabled={updateMutation.isPending}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Save className="h-4 w-4" aria-hidden="true" />
                    {updateMutation.isPending ? "Saving..." : "Save Changes"}
                  </button>
                </div>

                {updateMutation.error && (
                  <StateNotice
                    title="Failed to save edits"
                    description={updateMutation.error.message}
                    tone="error"
                  />
                )}

                {updateMutation.isSuccess && !updateMutation.error && (
                  <StateNotice
                    title="Document updated"
                    description="Your edits have been saved."
                    tone="info"
                  />
                )}
              </div>
            </Card>
          </form>

          <div className="space-y-4">
            <Card title="Factuality Audit" subtitle="Grounded against verified career profile">
              <dl className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Status</dt>
                  <dd className="font-semibold text-emerald-700">
                    {doc.factuality_report?.is_grounded ? "Grounded" : "Unverified"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Verified facts referenced</dt>
                  <dd className="font-mono text-slate-900">
                    {doc.factuality_report?.verified_fact_ids?.length ?? 0}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Claims validated</dt>
                  <dd className="font-mono text-slate-900">
                    {doc.factuality_report?.checked_claims_count ?? 0}
                  </dd>
                </div>
              </dl>
            </Card>

            <Card title="Version History" subtitle={`${doc.versions.length} saved version(s)`}>
              <ul className="space-y-2">
                {doc.versions.map((ver) => (
                  <li key={ver.id}>
                    <Link
                      to={`/documents/${ver.id}`}
                      className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors ${
                        ver.id === doc.id
                          ? "border-indigo-300 bg-indigo-50 text-indigo-900"
                          : "border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      <span className="font-semibold">Version v{ver.version}</span>
                      <StatusBadge
                        label={ver.is_user_edited ? "Edited" : "AI Draft"}
                        tone={ver.is_user_edited ? "warning" : "neutral"}
                      />
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
