export enum UserRole {
  AGENT = 'AGENT',
  TEAM_LEADER = 'TEAM_LEADER',
  MANAGER = 'MANAGER',
  ADMIN = 'ADMIN',
}

export interface User {
  id: string;
  phone: string;
  name: string;
  role: UserRole;
  avatar?: string;
  teamId?: string;
  teamName?: string;
  createdAt: string;
}

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedResponse<T> {
  code: number;
  message: string;
  data: {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
  };
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
}
