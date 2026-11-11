import { apiRequest, getApiBaseUrl } from "./api-client";
import type {
  AuthConfig,
  AuthSession,
  AuthUser,
  DevLoginPayload,
  LogoutResponse,
} from "../types/auth";

export const authService = {
  getConfig: (): Promise<AuthConfig> => apiRequest<AuthConfig>("/auth/config"),

  getGoogleLoginUrl: (redirectTo = "/"): string => {
    const encoded = encodeURIComponent(redirectTo);
    return `${getApiBaseUrl()}/auth/google?mode=redirect&redirect_to=${encoded}`;
  },

  getMe: (): Promise<AuthUser> => apiRequest<AuthUser>("/auth/me"),

  devLogin: (payload: DevLoginPayload): Promise<AuthSession> =>
    apiRequest<AuthSession>("/auth/dev-login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: (): Promise<LogoutResponse> =>
    apiRequest<LogoutResponse>("/auth/logout", {
      method: "POST",
    }),
};

