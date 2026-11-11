import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CalendarClock, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { applicationService } from "../../../services/application-service";
import { healthService } from "../../../services/health-service";
import {
  applicationStatusLabel,
  applicationStatusTone,
} from "../../../types/application";
import { formatDisplayDate } from "../../applications/utils/dates";

function statusTone(value: string): "success" | "warning" | "danger" | "neutral" {
  if (value === "ok" || value === "ready" || value === "healthy") return "success";
  if (value === "degraded" || value === "unavailable") return "warning";
  if (value === "unhealthy") return "danger";
  return "neutral";
}

export function FoundationStatusPage() {
  const livenessQuery = useQuery({
    queryKey: ["health", "liveness"],
    queryFn: healthService.getLiveness,
    retry: false,
  });

  const readinessQuery = useQuery({
    queryKey: ["health", "readiness"],
    queryFn: healthService.getReadiness,
    retry: false,
  });

  const summaryQuery = useQuery({
    queryKey: ["applications", "summary"],
    queryFn: applicationService.getSummary,
    retry: false,
  });

  const isLoading = livenessQuery.isPending || readinessQuery.isPending;
  const error = livenessQuery.error ?? readinessQuery.error;

  const refetchAll = () => {
    void livenessQuery.refetch();
    void readinessQuery.refetch();
    void summaryQuery.refetch();
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Platform Foundation Status
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Phase 1 architecture health, database connectivity, and dependency telemetry.
          </p>
        </div>
        <button
          type="button"
          onClick={refetchAll}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-2xs transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} aria-hidden="true" />
          Refresh Status
        </button>
      </header>

      {isLoading && (
        <StateNotice
          title="Checking backend services..."
          description="Querying /api/v1/health and /api/v1/health/ready."
          tone="info"
        />
      )}

      {error && (
        <StateNotice
          title="Backend connection error"
          description={
            error instanceof Error
              ? error.message
              : "Could not reach the CareerPilot FastAPI backend."
          }
          tone="error"
        />
      )}

      {!isLoading && !error && livenessQuery.data && readinessQuery.data && (
        <div className="grid gap-5 md:grid-cols-2">
          <Card
            title="API Process Liveness"
            subtitle="/api/v1/health"
            action={
              <StatusBadge
                label={livenessQuery.data.status.toUpperCase()}
                tone={statusTone(livenessQuery.data.status)}
              />
            }
          >
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Service</dt>
                <dd className="font-medium text-slate-900">{livenessQuery.data.service}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Version</dt>
                <dd className="font-mono text-slate-900">{livenessQuery.data.version}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Environment</dt>
                <dd className="font-mono text-slate-900">{livenessQuery.data.environment}</dd>
              </div>
            </dl>
          </Card>

          <Card
            title="Dependency Readiness"
            subtitle="/api/v1/health/ready"
            action={
              <StatusBadge
                label={readinessQuery.data.status.toUpperCase()}
                tone={statusTone(readinessQuery.data.status)}
              />
            }
          >
            <ul className="space-y-2.5 text-sm">
              {Object.entries(readinessQuery.data.dependencies).map(([name, info]) => (
                <li key={name} className="flex items-center justify-between">
                  <span className="capitalize text-slate-700">{name}</span>
                  <StatusBadge label={info.status} tone={statusTone(info.status)} />
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {summaryQuery.data && (
        <Card
          title="Application Pipeline Summary"
          subtitle="Live placement tracking counts and upcoming deadlines"
          action={
            <Link
              to="/applications"
              className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              Open Tracker
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          }
        >
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-4">
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Total Applications</p>
                <p className="mt-1 text-xl font-bold text-slate-900">
                  {summaryQuery.data.total_applications}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Preparing</p>
                <p className="mt-1 text-xl font-bold text-indigo-700">
                  {summaryQuery.data.counts_by_status["PREPARING"] ?? 0}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Submitted</p>
                <p className="mt-1 text-xl font-bold text-emerald-700">
                  {summaryQuery.data.counts_by_status["SUBMITTED"] ?? 0}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Interviews</p>
                <p className="mt-1 text-xl font-bold text-amber-700">
                  {summaryQuery.data.counts_by_status["INTERVIEW_SCHEDULED"] ?? 0}
                </p>
              </div>
            </div>

            {summaryQuery.data.upcoming_deadlines.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Upcoming Deadlines
                </h3>
                <ul className="mt-2 divide-y divide-slate-100 text-sm">
                  {summaryQuery.data.upcoming_deadlines.map((item) => (
                    <li
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-2 py-2 first:pt-0 last:pb-0"
                    >
                      <div>
                        <Link
                          to={`/applications/${item.id}`}
                          className="font-medium text-slate-900 hover:text-indigo-600"
                        >
                          {item.role_title}
                        </Link>
                        <span className="ml-2 text-xs text-slate-500">{item.company_name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge
                          label={applicationStatusLabel(item.status)}
                          tone={applicationStatusTone(item.status)}
                        />
                        <span className="inline-flex items-center gap-1 text-xs text-amber-700">
                          <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
                          {formatDisplayDate(item.deadline_at)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

