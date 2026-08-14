export interface LoginRequest {
  phone: string;
  verification_code?: string;
  password?: string;
}

export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserInfo {
  id: string;
  phone: string;
  name: string;
  avatar_url?: string;
  role_code: string;
  role_name: string;
  organization_id: string;
  team_id?: string;
  status: string;
  last_login_at?: string;
  demo_mode: boolean;
  created_at: string;
}
