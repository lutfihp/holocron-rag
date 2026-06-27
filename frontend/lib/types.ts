export type ClearanceLevel = 'public' | 'restricted' | 'secret' | 'top_secret';

export type Role = 'employee' | 'manager' | 'director' | 'executive';

export interface TenantSummary {
  id: string;
  name: string;
  role_label: string;
}

export interface UserSummary {
  id: string;
  username: string;
  role: Role;
  max_clearance: ClearanceLevel;
  departments: string[];
  tenant: TenantSummary;
}

export interface ApiError {
  status: number;
  detail: string;
}
