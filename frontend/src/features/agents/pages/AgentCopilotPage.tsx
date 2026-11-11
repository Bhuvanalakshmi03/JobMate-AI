import {
  Activity,
  Bot,
  Database,
  MessageSquare,
  Play,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import {
  workflowStatusTone,
  type WorkflowRun,
  type WorkflowTaskType,
} from "../../../types/agent";
import { formatDisplayDate } from "../../applications/utils/dates";
import { CopilotChatPanel } from "../../copilot/components/CopilotChatPanel";
import { useJobSearch } from "../../jobs/hooks/useJobs";
import { useResumesList } from "../../resume/hooks/useResumes";
import {
  useQueryRagMutation,
  useStartWorkflowMutation,
  useSyncRagMutation,
  useWorkflowsList,
} from "../hooks/useAgents";

export function AgentCopilotPage() {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "workflows" ? "workflows" : "chat";
  const calendarConnected = searchParams.get("calendar") === "connected";
  const [activeTab, setActiveTab] = useState<"chat" | "workflows">(initialTab);

  const workflowsQuery = useWorkflowsList();
  const jobsQuery = useJobSearch({ limit: 30 }, true);
  const resumesQuery = useResumesList();

  const startMutation = useStartWorkflowMutation();
  const syncRagMutation = useSyncRagMutation();
  const queryRagMutation = useQueryRagMutation();

  const [taskType, setTaskType] = useState<WorkflowTaskType>("auto");
  const [requestedTask, setRequestedTask] = useState("");
  const [jobId, setJobId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLocation, setSearchLocation] = useState("");
  const [ragSearch, setRagSearch] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("");

  const workflows = workflowsQuery.data?.items ?? [];

  useEffect(() => {
    if (!selectedWorkflowId && workflows.length > 0) {
      setSelectedWorkflowId(workflows[0].id);
    }
  }, [selectedWorkflowId, workflows]);

  const activeWorkflow: WorkflowRun | undefined =
    workflows.find((item) => item.id === selectedWorkflowId) ?? startMutation.data ?? workflows[0];

  const handleRunWorkflow = async (e: FormEvent) => {
    e.preventDefault();
    if (requestedTask.trim().length < 3) {
      setValidationError("Enter a workflow instruction of at least 3 characters.");
      return;
    }
    setValidationError(null);
    try {
      const created = await startMutation.mutateAsync({
        requested_task: requestedTask.trim(),
        task_type: taskType,
        job_id: jobId || null,
        resume_id: resumeId || null,
        search_query: searchQuery.trim() || null,
        search_location: searchLocation.trim() || null,
      });
      setSelectedWorkflowId(created.id);
    } catch {
      // Displayed via startMutation.error
    }
  };

  const handleSyncRag = async () => {
    try {
      await syncRagMutation.mutateAsync();
    } catch {
      // Displayed via syncRagMutation.error
    }
  };

  const handleQueryRag = async (e: FormEvent) => {
    e.preventDefault();
    if (ragSearch.trim().length < 2) return;
    try {
      await queryRagMutation.mutateAsync({ query: ragSearch.trim(), top_k: 5 });
    } catch {
      // Displayed via queryRagMutation.error
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">AI Agent Co-Pilot</h1>
          <p className="mt-1 text-sm text-slate-600">
            Session-managed AI chat with tool calling &amp; Google Calendar, plus LangGraph
            multi-agent orchestration with human approval gates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div
            role="tablist"
            aria-label="Co-Pilot Workspace Mode"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1"
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "chat"}
              onClick={() => setActiveTab("chat")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeTab === "chat"
                  ? "bg-white text-indigo-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
              Co-Pilot Chat &amp; Calendar
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "workflows"}
              onClick={() => setActiveTab("workflows")}
              className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeTab === "workflows"
                  ? "bg-white text-indigo-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Bot className="h-3.5 w-3.5" aria-hidden="true" />
              LangGraph Workflows &amp; RAG
            </button>
          </div>
          {activeTab === "workflows" && (
            <button
              type="button"
              disabled={syncRagMutation.isPending}
              onClick={() => void handleSyncRag()}
              className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
            >
              <Database className="h-4 w-4" aria-hidden="true" />
              {syncRagMutation.isPending ? "Indexing..." : "Sync Knowledge to ChromaDB"}
            </button>
          )}
        </div>
      </header>

      {activeTab === "chat" ? (
        <CopilotChatPanel calendarJustConnected={calendarConnected} />
      ) : (
        <>
          {syncRagMutation.data && (
            <StateNotice
              title="ChromaDB career index updated"
              description={`Indexed ${syncRagMutation.data.indexed_chunks} chunk(s) (${syncRagMutation.data.skipped_duplicates} duplicate(s) skipped).`}
              tone="info"
            />
          )}

          {syncRagMutation.error && (
            <StateNotice
              title="Knowledge indexing failed"
              description={syncRagMutation.error.message}
              tone="error"
            />
          )}

          <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card
            title="Launch Multi-Agent Workflow"
            subtitle="Route cleanly to specialist agents (Resume, Job Discovery, Matching, Documents, Advisory) with checkpoint persistence."
          >
            <form onSubmit={(e) => void handleRunWorkflow(e)} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label
                    htmlFor="copilot-mode"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Workflow Mode
                  </label>
                  <select
                    id="copilot-mode"
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value as WorkflowTaskType)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="auto">Auto Route (Workflow Classifier)</option>
                    <option value="application_prep">
                      Application Prep + Human Approval Gate
                    </option>
                    <option value="job_discovery">Job Discovery & Ranking</option>
                    <option value="career_advisory">RAG Career Advisory</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="copilot-job" className="block text-xs font-medium text-slate-700">
                    Target Job Listing (optional)
                  </label>
                  <select
                    id="copilot-job"
                    value={jobId}
                    onChange={(e) => setJobId(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="">None selected</option>
                    {(jobsQuery.data?.items ?? []).map((job) => (
                      <option key={job.id} value={job.id}>
                        {job.title} — {job.company}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="copilot-resume"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Verified Source Resume (optional)
                  </label>
                  <select
                    id="copilot-resume"
                    value={resumeId}
                    onChange={(e) => setResumeId(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="">Use all verified resume facts</option>
                    {(resumesQuery.data?.items ?? []).map((resume) => (
                      <option key={resume.id} value={resume.id}>
                        {resume.original_filename}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="copilot-location"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Search Location Override (optional)
                  </label>
                  <input
                    id="copilot-location"
                    type="text"
                    value={searchLocation}
                    onChange={(e) => setSearchLocation(e.target.value)}
                    placeholder="e.g., Remote or Bengaluru"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {!jobId && taskType !== "career_advisory" && (
                <div>
                  <label
                    htmlFor="copilot-search-query"
                    className="block text-xs font-medium text-slate-700"
                  >
                    Job Search Query Override (optional — used if no target job is selected)
                  </label>
                  <input
                    id="copilot-search-query"
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="e.g., Python FastAPI Backend Intern"
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label htmlFor="copilot-task" className="block text-xs font-medium text-slate-700">
                  Instruction for CareerPilot Agents
                </label>
                <textarea
                  id="copilot-task"
                  rows={3}
                  value={requestedTask}
                  onChange={(e) => setRequestedTask(e.target.value)}
                  placeholder="e.g., Prepare a tailored resume, cover letter, and approval request for this backend role."
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {validationError && (
                <StateNotice
                  title="Invalid instruction"
                  description={validationError}
                  tone="error"
                />
              )}

              {startMutation.error && (
                <StateNotice
                  title="Workflow launch failed"
                  description={startMutation.error.message}
                  tone="error"
                />
              )}

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={startMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  <Play className="h-4 w-4" aria-hidden="true" />
                  {startMutation.isPending ? "Running Agents..." : "Run Co-Pilot Workflow"}
                </button>
              </div>
            </form>
          </Card>

          {activeWorkflow && (
            <Card
              title="Workflow Run Inspection"
              subtitle={`Stage: ${activeWorkflow.current_stage} · Tokens: ${activeWorkflow.total_tokens_used}`}
              action={
                <StatusBadge
                  label={activeWorkflow.status}
                  tone={workflowStatusTone(activeWorkflow.status)}
                />
              }
            >
              <div className="space-y-4">
                <p className="text-sm text-slate-700">{activeWorkflow.user_request}</p>

                {activeWorkflow.status === "PAUSED_FOR_APPROVAL" && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-900">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1.5 font-semibold">
                        <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                        Paused at Human Approval Gate
                      </span>
                      <Link
                        to="/approvals"
                        className="rounded-md bg-amber-600 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-700"
                      >
                        Review & Confirm Action
                      </Link>
                    </div>
                    <p className="mt-1 text-xs text-amber-800">
                      Prepared application materials will not be submitted until you confirm in the
                      Approval Queue.
                    </p>
                  </div>
                )}

                {activeWorkflow.error_detail && (
                  <StateNotice
                    title="Workflow execution error"
                    description={activeWorkflow.error_detail}
                    tone="error"
                  />
                )}

                {Object.keys(activeWorkflow.agent_outputs).length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Specialist Outputs
                    </h3>
                    <pre className="max-h-72 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                      {JSON.stringify(activeWorkflow.agent_outputs, null, 2)}
                    </pre>
                  </div>
                )}

                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Execution Trace ({activeWorkflow.execution_trace.length} steps)
                  </h3>
                  <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-slate-50/60">
                    {activeWorkflow.execution_trace.map((step, idx) => (
                      <li
                        key={`${step.node}-${idx}`}
                        className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-xs"
                      >
                        <div>
                          <span className="font-mono font-semibold text-slate-900">
                            {step.node}
                          </span>
                          {step.detail && (
                            <span className="ml-2 text-slate-600">{step.detail}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-slate-500">
                          <StatusBadge
                            label={step.status}
                            tone={step.status === "failed" ? "danger" : "success"}
                          />
                          <span>{step.duration_ms}ms</span>
                          <span>attempts: {step.attempts}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card
            title="RAG Context Explorer"
            subtitle="Query user-isolated semantic memory indexed in ChromaDB."
          >
            <form onSubmit={(e) => void handleQueryRag(e)} className="space-y-3">
              <div>
                <label htmlFor="rag-query-input" className="sr-only">
                  Query career context
                </label>
                <input
                  id="rag-query-input"
                  type="text"
                  value={ragSearch}
                  onChange={(e) => setRagSearch(e.target.value)}
                  placeholder="e.g., FastAPI microservices project"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={queryRagMutation.isPending}
                className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                <Search className="h-3.5 w-3.5" aria-hidden="true" />
                {queryRagMutation.isPending ? "Searching..." : "Retrieve RAG Context"}
              </button>
            </form>

            {queryRagMutation.data && (
              <div className="mt-4 space-y-2">
                {queryRagMutation.data.hits.length === 0 ? (
                  <p className="text-xs text-slate-500">
                    No matching chunks yet. Click Sync Knowledge to ChromaDB first.
                  </p>
                ) : (
                  queryRagMutation.data.hits.map((hit) => (
                    <div
                      key={hit.chunk_id}
                      className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs"
                    >
                      <div className="flex items-center justify-between gap-2 font-semibold text-slate-800">
                        <span>{hit.label ?? hit.source_type ?? "Context"}</span>
                        <span className="text-indigo-600">{Math.round(hit.score * 100)}%</span>
                      </div>
                      <p className="mt-1 line-clamp-3 text-slate-600">{hit.text}</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </Card>

          <Card title="Workflow History" subtitle={`${workflows.length} recorded run(s)`}>
            {workflowsQuery.isPending && (
              <p className="text-xs text-slate-500">Loading workflow runs...</p>
            )}
            {workflowsQuery.error && (
              <StateNotice
                title="Unable to load workflows"
                description={workflowsQuery.error.message}
                tone="error"
              />
            )}
            {!workflowsQuery.isPending && !workflowsQuery.error && workflows.length === 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Sparkles className="h-4 w-4 text-indigo-500" aria-hidden="true" />
                <span>No workflow runs yet.</span>
              </div>
            )}
            <ul className="space-y-2">
              {workflows.map((wf) => (
                <li key={wf.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedWorkflowId(wf.id)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                      activeWorkflow?.id === wf.id
                        ? "border-indigo-300 bg-indigo-50/70"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-900">
                        <Activity className="h-3.5 w-3.5 text-indigo-600" aria-hidden="true" />
                        {wf.task_type}
                      </span>
                      <StatusBadge label={wf.status} tone={workflowStatusTone(wf.status)} />
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-slate-600">{wf.user_request}</p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {formatDisplayDate(wf.created_at)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
        </>
      )}
    </div>
  );
}

