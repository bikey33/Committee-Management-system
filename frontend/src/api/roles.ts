import { apiClient } from "./client";

export interface Permission {
  id: number;
  codename: string;
  name: string;
  group: string;
  description: string;
  is_active: boolean;
}

export interface Role {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  permissions: Permission[];
  user_count: number;
  created_at: string;
  updated_at: string;
}

export const rolesService = {
  getAll: (): Promise<Role[]> =>
    apiClient.get("/api/users/roles/").then((r) => r.data),

  create: (data: { name: string; description?: string }): Promise<Role> =>
    apiClient.post("/api/users/roles/create/", data).then((r) => r.data.data),

  update: (id: number, data: { name?: string; description?: string; is_active?: boolean }): Promise<Role> =>
    apiClient.patch(`/api/users/roles/${id}/`, data).then((r) => r.data.data),

  delete: (id: number): Promise<void> =>
    apiClient.delete(`/api/users/roles/${id}/delete/`).then(() => undefined),

  getPermissions: (roleId: number): Promise<Permission[]> =>
    apiClient.get(`/api/users/roles/${roleId}/permissions/`).then((r) => r.data),

  setPermissions: (roleId: number, codenames: string[]): Promise<void> =>
    apiClient.put(`/api/users/roles/${roleId}/permissions/`, { permissions: codenames }).then(() => undefined),

  getAllPermissions: (): Promise<Permission[]> =>
    apiClient.get("/api/users/permissions/").then((r) => r.data),
};
