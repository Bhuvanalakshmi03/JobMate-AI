export interface AuthConfig {
  google_oauth_enabled: boolean;
  dev_auth_enabled: boolean;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  oauth_provider: string;
  timezone: string;
  last_login_at?: string | null;
  created_at: string;
  is_demo_auth: boolean;
}

export interface AuthSession {
  user: AuthUser;
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  is_demo_auth: boolean;
}

export interface DevLoginPayload {
  email: string;
  full_name: string;
  timezone: string;
}

export interface LogoutResponse {
  logged_out: boolean;
  message: string;
}

