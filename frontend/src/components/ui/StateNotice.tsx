import type { ReactNode } from "react";

interface StateNoticeProps {
  title: string;
  description: string;
  tone?: "info" | "error" | "empty";
  action?: ReactNode;
}

const STYLES = {
  info: "border-indigo-200 bg-indigo-50/70 text-indigo-950",
  error: "border-rose-200 bg-rose-50 text-rose-950",
  empty: "border-slate-200 bg-slate-50 text-slate-800",
};

export function StateNotice({
  title,
  description,
  tone = "info",
  action,
}: StateNoticeProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`rounded-xl border p-4 ${STYLES[tone]}`}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold">{title}</p>
          <p className="mt-1 text-sm opacity-85">{description}</p>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}

