import { Sparkles } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { StateNotice } from "../../../components/ui/StateNotice";
import { WeeklyCalendarCard } from "../components/WeeklyCalendarCard";

export function WeeklyCalendarPage() {
  const [searchParams] = useSearchParams();
  const calendarConnected = searchParams.get("calendar") === "connected";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Weekly Calendar Schedule
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            All scheduled Google Calendar events strictly within 1 week from the current time, plus
            pending JobMate AI calendar proposals.
          </p>
        </div>
        <Link
          to="/copilot"
          className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Schedule with AI Co-Pilot
        </Link>
      </header>

      {calendarConnected && (
        <StateNotice
          title="Google Calendar connected"
          description="Your upcoming 7-day schedule is now synced below."
          tone="info"
        />
      )}

      <WeeklyCalendarCard redirectTo="/calendar" />
    </div>
  );
}
