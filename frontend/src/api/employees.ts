import { apiClient } from "./client";

export interface Employee {
  employee_id: string;
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  mno?: string | null;
  position?: string | null;
  level?: string | null;
  service?: string | null;
  group?: string | null;
  qualification?: string | null;
  seniority?: string | null;
  retirement?: string | null;
  department?: string | null;
  designation?: string | null;
  // Read-only, from the serializer:
  has_user_account?: boolean;
  user_employee_id?: string | null;
  user_email?: string | null;
}

export interface PaginatedEmployees {
  results: Employee[];
  count: number;
  total_pages: number;
  current_page: number;
  page_size: number;
}

export const employeesService = {
  list: async (page = 1, pageSize = 10, search = ""): Promise<PaginatedEmployees> => {
    const response = await apiClient.get("/api/users/employee-details/", {
      params: { page, page_size: pageSize, ...(search ? { search } : {}) },
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

  create: async (data: Partial<Employee>) => {
    const response = await apiClient.post("/api/users/employee-details/create/", data);
    return response.data;
  },

  update: async (employeeId: string, data: Partial<Employee>) => {
    const response = await apiClient.patch(
      `/api/users/employee-details/${employeeId}/`,
      data
    );
    return response.data;
  },
};
