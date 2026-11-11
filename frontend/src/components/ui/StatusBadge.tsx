type Tone = "success" | "warning" | "danger" | "neutral" | "info";

interface StatusBadgeProps {
  label: string;
  tone?: Tone;
}

const TONE_CLASSES: Record<Tone, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  warning: "bg-amber-50 text-amber-700 ring-amber-600/20",
  danger: "bg-rose-50 text-rose-700 ring-rose-600/20",
  info: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  neutral: "bg-slate-100 text-slate-700 ring-slate-500/20",
};

export function StatusBadge({ label, tone = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}

