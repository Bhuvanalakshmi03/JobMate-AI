import { Check, Pencil, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { FactPatchItem, ResumeFact } from "../../../types/resume";

interface ResumeFactCardProps {
  fact: ResumeFact;
  isSubmitting: boolean;
  onAction: (patch: FactPatchItem) => Promise<unknown>;
}

function verificationTone(
  status: string
): "success" | "warning" | "danger" | "info" | "neutral" {
  if (status === "verified" || status === "edited") return "success";
  if (status === "rejected") return "danger";
  return "warning";
}

export function ResumeFactCard({ fact, isSubmitting, onAction }: ResumeFactCardProps) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(fact.title);
  const [organization, setOrganization] = useState(fact.organization ?? "");
  const [startDate, setStartDate] = useState(fact.start_date ?? "");
  const [endDate, setEndDate] = useState(fact.end_date ?? "");
  const [description, setDescription] = useState(fact.description ?? "");

  const evidenceMatched = fact.structured_data?.evidence_matched !== false;
  const confidencePct = Math.round(fact.confidence * 100);

  const handleSaveEdit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onAction({
      fact_id: fact.id,
      action: "edit",
      title: title.trim(),
      organization: organization.trim() || null,
      start_date: startDate.trim() || null,
      end_date: endDate.trim() || null,
      description: description.trim() || null,
    });
    setEditing(false);
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={fact.fact_type.replace("_", " ")} tone="info" />
            <StatusBadge
              label={fact.verification_status}
              tone={verificationTone(fact.verification_status)}
            />
            <StatusBadge
              label={`${confidencePct}% confidence`}
              tone={evidenceMatched && confidencePct >= 70 ? "neutral" : "warning"}
            />
            {!evidenceMatched && <StatusBadge label="Unverified excerpt" tone="danger" />}
          </div>
          <h3 className="text-sm font-semibold text-slate-900">{fact.title}</h3>
          {(fact.organization || fact.start_date || fact.end_date) && (
            <p className="text-xs text-slate-600">
              {[fact.organization, [fact.start_date, fact.end_date].filter(Boolean).join(" – ")]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void onAction({ fact_id: fact.id, action: "verify" })}
            className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            Verify
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => setEditing((prev) => !prev)}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Edit
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={() => void onAction({ fact_id: fact.id, action: "reject" })}
            className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Reject
          </button>
        </div>
      </div>

      {fact.description && !editing && (
        <p className="mt-2.5 text-sm leading-relaxed text-slate-700">{fact.description}</p>
      )}

      {(fact.source_section || fact.evidence_excerpt) && (
        <blockquote className="mt-3 rounded-lg border-l-2 border-indigo-400 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {fact.source_section && (
            <span className="mr-1.5 font-semibold text-slate-700">[{fact.source_section}]</span>
          )}
          {fact.evidence_excerpt}
        </blockquote>
      )}

      {editing && (
        <form onSubmit={handleSaveEdit} className="mt-3 space-y-3 border-t border-slate-200 pt-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-slate-700">Title</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Organization</label>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">Start date</label>
              <input
                type="text"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700">End date</label>
              <input
                type="text"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Save & Verify
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
