import { BrainCircuit, Download, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { authService } from "../../../services/auth-service";
import type { MemoryCategory } from "../../../types/memory";
import { formatDisplayDate } from "../../applications/utils/dates";
import { useAuth } from "../../authentication/hooks/useAuth";
import {
  useClearAllMemoryMutation,
  useCreateMemoryMutation,
  useDeleteMemoryMutation,
  useMemoriesList,
  useUpdateMemoryConsentMutation,
  useUpdateMemoryMutation,
} from "../hooks/useMemory";

export function MemoryAndPrivacyPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [categoryFilter, setCategoryFilter] = useState("");
  const memoriesQuery = useMemoriesList(categoryFilter);

  const consentMutation = useUpdateMemoryConsentMutation();
  const createMutation = useCreateMemoryMutation();
  const updateMutation = useUpdateMemoryMutation();
  const deleteMutation = useDeleteMemoryMutation();
  const clearAllMutation = useClearAllMemoryMutation();

  const [newCategory, setNewCategory] = useState<MemoryCategory>("preference");
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [lifecycleError, setLifecycleError] = useState<string | null>(null);
  const [deletingAccount, setDeletingAccount] = useState(false);

  const consent = memoriesQuery.data?.consent ?? {
    ai_consent_given: false,
    notification_consent: false,
  };
  const items = memoriesQuery.data?.items ?? [];

  const handleCreateMemory = async (e: FormEvent) => {
    e.preventDefault();
    if (newTitle.trim().length < 2 || newContent.trim().length < 3) return;
    try {
      await createMutation.mutateAsync({
        category: newCategory,
        title: newTitle.trim(),
        content: newContent.trim(),
        is_approved: true,
      });
      setNewTitle("");
      setNewContent("");
    } catch {
      // Displayed via createMutation.error
    }
  };

  const handleExportData = async () => {
    setLifecycleError(null);
    setExportNotice(null);
    try {
      const payload = await authService.exportMyData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `jobmate-ai-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportNotice("Your JobMate AI personal data export has been downloaded.");
    } catch (err) {
      setLifecycleError(err instanceof Error ? err.message : "Failed to export account data.");
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmText.trim() !== "DELETE") return;
    setLifecycleError(null);
    setDeletingAccount(true);
    try {
      await authService.deleteAccount();
      await logout();
      navigate("/login", { replace: true });
    } catch (err) {
      setDeletingAccount(false);
      setLifecycleError(err instanceof Error ? err.message : "Failed to delete account.");
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Career Memory &amp; Privacy Controls
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Control what long-term preferences JobMate AI Co-Pilot remembers, toggle notifications, and
          export or delete your account data anytime.
        </p>
      </header>

      <Card
        title="Consent & Personalization Settings"
        subtitle="Persistent Career Memory is saved and injected into Co-Pilot Chat only when you opt in."
        action={
          <StatusBadge
            label={consent.ai_consent_given ? "MEMORY OPT-IN" : "CONSENT OFF"}
            tone={consent.ai_consent_given ? "success" : "warning"}
          />
        }
      >
        <div className="space-y-3 text-sm">
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
            <input
              type="checkbox"
              checked={consent.ai_consent_given}
              disabled={consentMutation.isPending}
              onChange={(e) =>
                void consentMutation.mutateAsync({
                  ai_consent_given: e.target.checked,
                  notification_consent: consent.notification_consent,
                })
              }
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600"
            />
            <div>
              <p className="font-semibold text-slate-900">Allow Career Memory &amp; AI Co-Pilot</p>
              <p className="text-xs text-slate-600">
                Persist user-approved preferences, target goals, and interview notes across sessions.
              </p>
            </div>
          </label>

          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-3 hover:bg-slate-50">
            <input
              type="checkbox"
              checked={consent.notification_consent}
              disabled={consentMutation.isPending}
              onChange={(e) =>
                void consentMutation.mutateAsync({
                  ai_consent_given: consent.ai_consent_given,
                  notification_consent: e.target.checked,
                })
              }
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600"
            />
            <div>
              <p className="font-semibold text-slate-900">Allow External Digest Notifications</p>
              <p className="text-xs text-slate-600">
                Permit scheduled reminder notifications on digest channels (in-app notifications are
                always safe and deduplicated).
              </p>
            </div>
          </label>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <Card
            title="Save Approved Memory"
            subtitle="Only items you explicitly save or approve are retained."
          >
            <form onSubmit={(e) => void handleCreateMemory(e)} className="space-y-3 text-xs">
              <div>
                <label htmlFor="mem-cat" className="block font-medium text-slate-700">
                  Category
                </label>
                <select
                  id="mem-cat"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value as MemoryCategory)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="preference">Role / Location Preference</option>
                  <option value="goal">Career Goal</option>
                  <option value="strength">Verified Strength</option>
                  <option value="weakness">Growth Area</option>
                  <option value="note">General Note</option>
                </select>
              </div>
              <div>
                <label htmlFor="mem-title" className="block font-medium text-slate-700">
                  Memory Title
                </label>
                <input
                  id="mem-title"
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g., Target Salary & Location"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div>
                <label htmlFor="mem-content" className="block font-medium text-slate-700">
                  Detail
                </label>
                <textarea
                  id="mem-content"
                  rows={3}
                  required
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="e.g., Focusing on Python/FastAPI AI roles in Chennai or Bengaluru."
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              {createMutation.error && (
                <StateNotice
                  title="Unable to save memory"
                  description={createMutation.error.message}
                  tone="error"
                />
              )}
              <button
                type="submit"
                disabled={createMutation.isPending || !consent.ai_consent_given}
                className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                {createMutation.isPending ? "Saving..." : "Save Career Memory"}
              </button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-7">
          <Card
            title="Stored Career Memory"
            subtitle={`${items.length} memory entry(s)`}
            action={
              <div className="flex items-center gap-2">
                <select
                  aria-label="Filter memories by category"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs"
                >
                  <option value="">All Categories</option>
                  <option value="preference">Preferences</option>
                  <option value="goal">Goals</option>
                  <option value="strength">Strengths</option>
                  <option value="weakness">Growth Areas</option>
                  <option value="note">Notes</option>
                </select>
                {items.length > 0 && (
                  <button
                    type="button"
                    onClick={() => void clearAllMutation.mutateAsync()}
                    disabled={clearAllMutation.isPending}
                    className="rounded-lg border border-rose-200 px-2.5 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50"
                  >
                    Clear All
                  </button>
                )}
              </div>
            }
          >
            {memoriesQuery.isPending ? (
              <p className="text-xs text-slate-500">Loading stored Career Memory...</p>
            ) : items.length === 0 ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <BrainCircuit className="h-4 w-4 text-indigo-500" aria-hidden="true" />
                <span>No Career Memory entries yet.</span>
              </div>
            ) : (
              <ul className="space-y-2.5">
                {items.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-900">{item.title}</p>
                        <p className="mt-1 text-slate-700">{item.content}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <StatusBadge
                          label={item.category}
                          tone={item.is_approved && item.is_active ? "info" : "neutral"}
                        />
                        <button
                          type="button"
                          aria-label={`Toggle approval for ${item.title}`}
                          onClick={() =>
                            void updateMutation.mutateAsync({
                              memoryId: item.id,
                              payload: { is_approved: !item.is_approved },
                            })
                          }
                          className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-700 hover:bg-slate-100"
                        >
                          {item.is_approved ? "Pause" : "Approve"}
                        </button>
                        <button
                          type="button"
                          aria-label={`Delete memory ${item.title}`}
                          onClick={() => void deleteMutation.mutateAsync(item.id)}
                          className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="mt-1.5 text-[11px] text-slate-400">
                      Source: {item.source} · Updated {formatDisplayDate(item.updated_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Card
        title="Account Data Export & Deletion"
        subtitle="Download a complete copy of your career data or permanently erase your account."
        action={<ShieldCheck className="h-4 w-4 text-emerald-600" aria-hidden="true" />}
      >
        <div className="space-y-4">
          {exportNotice && (
            <StateNotice title="Export ready" description={exportNotice} tone="info" />
          )}
          {lifecycleError && (
            <StateNotice title="Account action failed" description={lifecycleError} tone="error" />
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-3.5">
            <div>
              <p className="text-sm font-semibold text-slate-900">Export Personal Career Data</p>
              <p className="text-xs text-slate-600">
                Includes profile, skills, verified facts, applications, interviews, memories, and
                reminders (excluding internal secrets).
              </p>
            </div>
            <button
              type="button"
              onClick={() => void handleExportData()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Export JSON
            </button>
          </div>

          <div className="space-y-2 rounded-lg border border-rose-200 bg-rose-50/40 p-3.5">
            <p className="text-sm font-semibold text-rose-900">Delete Account Permanently</p>
            <p className="text-xs text-rose-700">
              Type <strong>DELETE</strong> below to permanently delete your JobMate AI account,
              resumes, applications, memories, and sessions.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                aria-label="Confirm account deletion by typing DELETE"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                placeholder="Type DELETE to confirm"
                className="rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs focus:outline-none"
              />
              <button
                type="button"
                disabled={deleteConfirmText.trim() !== "DELETE" || deletingAccount}
                onClick={() => void handleDeleteAccount()}
                className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {deletingAccount ? "Deleting Account..." : "Delete My Account"}
              </button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
