import { apiClient } from "./client";

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
  role?: string;
  office_name?: string;
}

export const usersService = {
  getAll: async () => {
    const response = await apiClient.get("/api/users/users/");
    if (response.data?.results) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
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

  // Standard register
  register: async (data: any) => {
    const response = await apiClient.post("/api/users/register/", data);
    return response.data;
  },

  getRoles: async () => {
    const response = await apiClient.get("/api/users/roles/");
    return response.data;
  },
};
