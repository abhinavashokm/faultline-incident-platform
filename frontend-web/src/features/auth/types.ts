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
}

export interface AuthResponse {
  token: string;
  user: User;
  workspace: Workspace;
}

export interface VerificationResponse {
  status: "pending_verification" | "verified";
  email: string;
  expiresInSeconds: number;
}

