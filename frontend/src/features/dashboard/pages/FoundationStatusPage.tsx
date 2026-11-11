import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { healthService } from "../../../services/health-service";

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

  const isLoading = livenessQuery.isPending || readinessQuery.isPending;
  const error = livenessQuery.error ?? readinessQuery.error;

  const refetchAll = () => {
    void livenessQuery.refetch();
    void readinessQuery.refetch();
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
    </div>
  );
}

