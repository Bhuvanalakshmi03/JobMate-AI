import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { StateNotice } from "../../../components/ui/StateNotice";
import { useAuth } from "../hooks/useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl py-16">
        <StateNotice
          title="Verifying your session..."
          description="Checking your authenticated JobMate AI session."
          tone="info"
        />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

