export interface User {
  id: string;
  name: string;
  email: string;
  avatarUrl?: string;
}

export interface Workspace {
  id: string;
  slug: string;
  name: string;
  role?: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  workspace?: Workspace | null;
}

export interface VerificationResponse {
  status: "pending_verification" | "verified";
  email: string;
  expiresInSeconds: number;
}

