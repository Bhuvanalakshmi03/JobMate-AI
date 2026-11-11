import { CheckCircle2, ExternalLink, ShieldCheck, XCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  approvalActionLabel,
  approvalStatusTone,
  type ApprovalStatus,
} from "../../../types/approval";
import { formatDisplayDate } from "../../applications/utils/dates";
import {
  useApproveActionMutation,
  useApprovalsList,
  useRejectActionMutation,
} from "../hooks/useApprovals";

const FILTER_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "All Requests" },
  { value: "PENDING", label: "Pending" },
  { value: "EXECUTED", label: "Executed" },
  { value: "REJECTED", label: "Rejected" },
];

export function ApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("PENDING");
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});

  const listQuery = useApprovalsList(statusFilter);
  const approveMutation = useApproveActionMutation();
  const rejectMutation = useRejectActionMutation();

  const handleDecision = async (approvalId: string, action: "approve" | "reject") => {
    const note = (decisionNotes[approvalId] ?? "").trim() || null;
    try {
      if (action === "approve") {
        await approveMutation.mutateAsync({ approvalId, note });
      } else {
        await rejectMutation.mutateAsync({ approvalId, note });
      }
      setDecisionNotes((prev) => {
        const next = { ...prev };
        delete next[approvalId];
        return next;
      });
    } catch {
      // Displayed via mutation error StateNotice
    }
  };

  const items = listQuery.data?.items ?? [];
  const pendingCount = listQuery.data?.pending_count ?? 0;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Human Approval Queue
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Review exact external destinations and prepared materials before any submission or
            outreach runs.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2 text-xs font-semibold text-amber-800">
          <ShieldCheck className="h-4 w-4" aria-hidden="true" />
          <span>{pendingCount} Pending Approval(s)</span>
        </div>
      </header>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter approvals">
        {FILTER_OPTIONS.map((option) => (
          <button
            key={option.value || "all"}
            type="button"
            onClick={() => setStatusFilter(option.value as ApprovalStatus | "")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              statusFilter === option.value
                ? "bg-indigo-600 text-white"
                : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {approveMutation.error && (
        <StateNotice
          title="Approval execution failed"
          description={approveMutation.error.message}
          tone="error"
        />
      )}

      {rejectMutation.error && (
        <StateNotice
          title="Rejection failed"
          description={rejectMutation.error.message}
          tone="error"
        />
      )}

      <Card
        title="Approval Requests"
        subtitle="Human confirmation is strictly required prior to external submission."
      >
        {listQuery.isPending && (
          <StateNotice
            title="Loading approval queue..."
            description="Fetching prepared external actions awaiting confirmation."
            tone="info"
          />
        )}

        {listQuery.error && (
          <StateNotice
            title="Unable to load approvals"
            description={listQuery.error.message}
            tone="error"
          />
        )}

        {!listQuery.isPending && !listQuery.error && items.length === 0 && (
          <StateNotice
            title="No matching approval requests"
            description="Launch an Application Prep workflow in AI Co-Pilot or request approval from an application page."
            tone="info"
          />
        )}

        {!listQuery.isPending && !listQuery.error && items.length > 0 && (
          <div className="space-y-4">
            {items.map((item) => {
              const isHttpDest = item.target_destination.startsWith("http");
              return (
                <div
                  key={item.id}
                  className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-base font-semibold text-slate-900">{item.title}</h2>
                        <StatusBadge
                          label={item.status}
                          tone={approvalStatusTone(item.status)}
                        />
                        <StatusBadge label={approvalActionLabel(item.action_type)} tone="info" />
                      </div>
                      <p className="mt-1 text-xs text-slate-600">
                        Target Destination:{" "}
                        {isHttpDest ? (
                          <a
                            href={item.target_destination}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 font-medium text-indigo-600 hover:underline"
                          >
                            {item.target_destination}
                            <ExternalLink className="h-3 w-3" aria-hidden="true" />
                          </a>
                        ) : (
                          <span className="font-medium text-slate-800">
                            {item.target_destination}
                          </span>
                        )}
                      </p>
                    </div>

                    {item.application_id && (
                      <Link
                        to={`/applications/${item.application_id}`}
                        className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                      >
                        View Application
                      </Link>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Prepared Payload Review
                    </p>
                    <pre className="mt-1 max-h-48 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                      {JSON.stringify(item.payload, null, 2)}
                    </pre>
                  </div>

                  <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
                    <span>Requested: {formatDisplayDate(item.created_at)}</span>
                    {item.decided_at && <span>Decided: {formatDisplayDate(item.decided_at)}</span>}
                    {item.executed_at && (
                      <span>Executed: {formatDisplayDate(item.executed_at)}</span>
                    )}
                  </div>

                  {item.decision_note && (
                    <p className="rounded-md bg-white px-3 py-2 text-xs text-slate-700 ring-1 ring-slate-200">
                      Decision Note: {item.decision_note}
                    </p>
                  )}

                  {item.status === "PENDING" && (
                    <div className="space-y-3 border-t border-slate-200 pt-3">
                      <div>
                        <label
                          htmlFor={`decision-note-${item.id}`}
                          className="block text-xs font-medium text-slate-700"
                        >
                          Decision Note (optional)
                        </label>
                        <input
                          id={`decision-note-${item.id}`}
                          type="text"
                          value={decisionNotes[item.id] ?? ""}
                          onChange={(e) =>
                            setDecisionNotes((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          placeholder="Confirm materials reviewed or explain rejection reason..."
                          className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                        />
                      </div>

                      <div className="flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          disabled={approveMutation.isPending || rejectMutation.isPending}
                          onClick={() => void handleDecision(item.id, "reject")}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                        >
                          <XCircle className="h-4 w-4" aria-hidden="true" />
                          Reject Action
                        </button>
                        <button
                          type="button"
                          disabled={approveMutation.isPending || rejectMutation.isPending}
                          onClick={() => void handleDecision(item.id, "approve")}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                          Approve & Execute
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}

