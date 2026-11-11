import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, type ReactNode } from "react";

import { ApiClientError, setUnauthorizedHandler } from "../../../services/api-client";
import { authService } from "../../../services/auth-service";
import type { AuthUser, DevLoginPayload } from "../../../types/auth";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  devLogin: (payload: DevLoginPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await authService.getMe();
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 401) {
          return null;
        }
        throw err;
      }
    },
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.removeQueries({ queryKey: ["profile"] });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  const devLogin = useCallback(
    async (payload: DevLoginPayload): Promise<AuthUser> => {
      const session = await authService.devLogin(payload);
      queryClient.setQueryData(["auth", "me"], session.user);
      return session.user;
    },
    [queryClient]
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.clear();
    }
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
  }, [queryClient]);

  const user = meQuery.data ?? null;

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading: meQuery.isPending,
        isAuthenticated: Boolean(user),
        devLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

