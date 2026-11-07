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

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  status: string;
  created_at: string;
  workspace?: Workspace | null;
}

export interface ResendVerificationResponse {
  message: string;
}


