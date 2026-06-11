import { apiClient } from "./client";
import type { MyCommitteesReport } from "./committees";

export interface User {
  id?: number;
  _id?: string;
  employee_id: string;
  employeeId?: string;
  username: string;
  email: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  isActive?: boolean;
  role?: string;
  user_role?: { id: number; name: string } | null;
  user_role_details?: { id: number; name: string } | null;
  office_name?: string;
  working_office?: string | null;
}

export interface PaginatedUsers {
  results: User[];
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
}

export const usersService = {
  getAll: async () => {
    const response = await apiClient.get("/api/users/users/");
    if (response.data?.results) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  // Server-side paginated list (backend UserListView supports page / page_size).
  list: async (page = 1, pageSize = 10): Promise<PaginatedUsers> => {
    const response = await apiClient.get("/api/users/users/", {
      params: { page, page_size: pageSize },
    });
    const data = response.data || {};
    const results = Array.isArray(data) ? data : data.results || [];
    return {
      results,
      count: data.count ?? results.length,
      total_pages: data.total_pages ?? 1,
      current_page: data.current_page ?? page,
      page_size: data.page_size ?? pageSize,
    };
  },

  getById: async (employeeId: string) => {
    const response = await apiClient.get(`/api/users/users/${employeeId}/`);
    return response.data;
  },

  // Gets employees that haven't been registered as users yet
  getAvailableEmployees: async () => {
    const response = await apiClient.get("/api/users/employees/available-for-users/");
    if (response.data?.data) {
      return response.data.data;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  createFromEmployee: async (data: { employee_id: string; role_id?: number }) => {
    const response = await apiClient.post("/api/users/users/create-from-employee/", data);
    return response.data;
  },

  update: async (
    employeeId: string,
    data: { name?: string; email?: string; isActive?: boolean; user_role_id?: number }
  ) => {
    const response = await apiClient.patch(`/api/users/users/${employeeId}/`, data);
    return response.data;
  },

  remove: async (employeeId: string) => {
    const response = await apiClient.delete(`/api/users/users/${employeeId}/`);
    return response.data;
  },

  // Standard register
  register: async (data: any) => {
    const response = await apiClient.post("/api/users/register/", data);
    return response.data;
  },

  getRoles: async () => {
    const response = await apiClient.get("/api/users/roles/");
    return response.data;
  },

  getUserMemberships: async (employeeId: string): Promise<MyCommitteesReport> => {
    const response = await apiClient.get(`/api/users/users/${employeeId}/memberships/`);
    return response.data?.data ?? { active: [], past: [], counts: { active: 0, past: 0 } };
  },
};
