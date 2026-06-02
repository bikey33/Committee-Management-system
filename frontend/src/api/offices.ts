import { apiClient } from "./client";

export interface Office {
  id: number;
  name: string;
  code: string;
  directorate?: number | null;
  directorate_name?: string | null;
  directorate_details?: Directorate | null;
  created_at?: string;
  updated_at?: string;
}

export interface Directorate {
  id: number;
  name: string;
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

  getDirectorates: async () => {
    const response = await apiClient.get("/api/users/directorates/");
    return response.data;
  },

  createDirectorate: async (data: Partial<Directorate>) => {
    const response = await apiClient.post("/api/users/directorates/create/", data);
    return response.data;
  },

  updateDirectorate: async (id: number, data: Partial<Directorate>) => {
    const response = await apiClient.put(`/api/users/directorates/${id}/`, data);
    return response.data;
  },

  deleteDirectorate: async (id: number) => {
    const response = await apiClient.delete(`/api/users/directorates/${id}/delete/`);
    return response.data;
  },
};
