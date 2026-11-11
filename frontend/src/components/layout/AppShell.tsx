import {
  Briefcase,
  Compass,
  FilePenLine,
  FileText,
  Layers,
  LogOut,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../../features/authentication/hooks/useAuth";
import { StatusBadge } from "../ui/StatusBadge";

interface AppShellProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  { to: "/", label: "System Foundation", icon: Layers },
  { to: "/profile", label: "Career Profile", icon: UserCheck },
  { to: "/resumes", label: "Resume Intelligence", icon: FileText },
  { to: "/jobs", label: "Job Discovery", icon: Briefcase },
  { to: "/documents", label: "Document Studio", icon: FilePenLine },
];

export function AppShell({ children }: AppShellProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 md:flex-row">
      <aside className="flex w-full shrink-0 flex-col justify-between border-b border-slate-800 bg-slate-950 text-slate-100 md:w-64 md:border-r md:border-b-0">
        <div>
          <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <Compass className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-white">CareerPilot AI</p>
              <p className="text-xs text-slate-400">Placement Co-Pilot</p>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="space-y-1 p-3">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-indigo-600 text-white"
                      : "text-slate-300 hover:bg-slate-900 hover:text-white"
                  }`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="space-y-3 border-t border-slate-800 p-4 text-xs text-slate-400">
          {user && (
            <div className="space-y-2 rounded-lg bg-slate-900/90 p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate font-semibold text-slate-100">{user.full_name}</p>
                {user.is_demo_auth && <StatusBadge label="DEV" tone="warning" />}
              </div>
              <p className="truncate text-slate-400">{user.email}</p>
              <button
                type="button"
                onClick={() => void handleLogout()}
                className="flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-800"
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                Sign out
              </button>
            </div>
          )}

          <div className="flex items-center gap-2 text-slate-300">
            <ShieldCheck className="h-4 w-4 text-emerald-400" aria-hidden="true" />
            <span>Human-approved actions enforced</span>
          </div>
        </div>
      </aside>

      <main className="flex-1 px-4 py-6 sm:px-8">{children}</main>
    </div>
  );
}
