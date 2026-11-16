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

export interface Membership {
  workspace_id: string;
  name: string;
  slug: string;
  role: string;
}

export interface CurrentUserResponse {
  id: string;
  email: string;
  full_name: string;
  status: string;
  email_verified_at?: string | null;
  created_at: string;
  workspace?: Workspace | null;
  memberships?: Membership[];
}

export interface ResendVerificationResponse {
  message: string;
}


