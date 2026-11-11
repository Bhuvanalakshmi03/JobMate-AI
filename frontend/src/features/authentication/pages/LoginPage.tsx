import { useQuery } from "@tanstack/react-query";
import { Compass, LockKeyhole, ShieldAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import { authService } from "../../../services/auth-service";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { isAuthenticated, isLoading, devLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fromPath =
    (location.state as { from?: string } | null)?.from && typeof location.state === "object"
      ? (location.state as { from: string }).from
      : "/";

  const configQuery = useQuery({
    queryKey: ["auth", "config"],
    queryFn: authService.getConfig,
    retry: false,
  });

  const [devEmail, setDevEmail] = useState("student@jobmate.local");
  const [devName, setDevName] = useState("Demo Student");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isLoading && isAuthenticated) {
    return <Navigate to={fromPath} replace />;
  }

  const handleGoogleSignIn = () => {
    window.location.assign(authService.getGoogleLoginUrl(fromPath));
  };

  const handleDevSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSubmitting(true);
    try {
      await devLogin({
        email: devEmail.trim(),
        full_name: devName.trim(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
      navigate(fromPath, { replace: true });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Development sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <Compass className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900">
            Sign in to JobMate AI
          </h1>
          <p className="mt-1.5 text-sm text-slate-600">
            Your human-approved placement co-pilot for resumes, job matching, and interview prep.
          </p>
        </div>

        <Card>
          {configQuery.isPending && (
            <StateNotice
              title="Loading authentication options..."
              description="Checking available sign-in methods."
              tone="info"
            />
          )}

          {configQuery.error && (
            <StateNotice
              title="Unable to reach authentication server"
              description={
                configQuery.error instanceof Error
                  ? configQuery.error.message
                  : "Please ensure the FastAPI backend is running."
              }
              tone="error"
            />
          )}

          {configQuery.data && (
            <div className="space-y-5">
              {configQuery.data.google_oauth_enabled ? (
                <button
                  type="button"
                  onClick={handleGoogleSignIn}
                  className="flex w-full items-center justify-center gap-2.5 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-indigo-700"
                >
                  <LockKeyhole className="h-4 w-4" aria-hidden="true" />
                  Continue with Google
                </button>
              ) : (
                <StateNotice
                  title="Google OAuth not yet configured"
                  description="Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend .env to enable Google OAuth 2.0 / OIDC login."
                  tone="empty"
                />
              )}

              {configQuery.data.dev_auth_enabled && (
                <form
                  onSubmit={handleDevSubmit}
                  className="space-y-3 rounded-lg border border-amber-200 bg-amber-50/70 p-4"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-900">
                      <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                      Local Development Sign-In
                    </span>
                    <StatusBadge label="DEV ONLY" tone="warning" />
                  </div>

                  <div>
                    <label
                      htmlFor="dev-email"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Email
                    </label>
                    <input
                      id="dev-email"
                      type="email"
                      required
                      value={devEmail}
                      onChange={(e) => setDevEmail(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="dev-name"
                      className="block text-xs font-medium text-slate-700"
                    >
                      Full name
                    </label>
                    <input
                      id="dev-name"
                      type="text"
                      required
                      value={devName}
                      onChange={(e) => setDevName(e.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                    />
                  </div>

                  {errorMessage && (
                    <p role="alert" className="text-xs font-medium text-rose-700">
                      {errorMessage}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full rounded-lg border border-amber-300 bg-white px-3.5 py-2 text-sm font-semibold text-amber-900 transition-colors hover:bg-amber-100 disabled:opacity-50"
                  >
                    {submitting ? "Signing in..." : "Sign in (Dev Mode)"}
                  </button>
                </form>
              )}

              <p className="text-xs leading-relaxed text-slate-500">
                Privacy notice: Your profile, resumes, and job preferences are isolated to your
                account. External submissions or recruiter actions always require your explicit
                approval.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

