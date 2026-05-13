import { apiClient } from "./client";

export interface Office {
  id: number;
  name: string;
  code: string;
  parent?: number | null;
  parent_name?: string; // Often APIs serialize a readable parent name
  department?: number | null;
  department_name?: string | null;
  department_details?: Department | null;
  departments?: string[];
  created_at?: string;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description?: string;
  office_count?: number;
  created_at?: string;
  updated_at?: string;
}

export const officesService = {
  getAll: async () => {
    const response = await apiClient.get("/api/users/offices/");
    return response.data;
  },

  getById: async (id: number) => {
    const response = await apiClient.get(`/api/users/offices/${id}/`);
    return response.data;
  },

  create: async (data: Partial<Office>) => {
    const response = await apiClient.post("/api/users/offices/create/", data);
    return response.data;
  },

  update: async (id: number, data: Partial<Office>) => {
    const response = await apiClient.put(`/api/users/offices/${id}/`, data);
    return response.data;
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/api/users/offices/${id}/delete/`);
    return response.data;
  },

  getDepartments: async () => {
    const response = await apiClient.get("/api/users/departments/");
    return response.data;
  },

  createDepartment: async (data: Partial<Department>) => {
    const response = await apiClient.post("/api/users/departments/create/", data);
    return response.data;
  },

  deleteDepartment: async (id: number) => {
    const response = await apiClient.delete(`/api/users/departments/${id}/delete/`);
    return response.data;
  },
};
