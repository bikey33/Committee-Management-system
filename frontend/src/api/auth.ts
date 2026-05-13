import { apiClient } from "./client";

export const authService = {
  login: async (employee_id: string, password: string) => {
    // The backend uses employee_id as the primary identifier instead of username
    const response = await apiClient.post("/api/users/token/", {
      employee_id,
      password,
    });
    
    const { access, refresh } = response.data;
    
    // Store tokens
    if (access) localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
    
    return response.data;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    window.location.href = "/login";
  },

  isAuthenticated: () => {
    return !!localStorage.getItem("access_token");
  },

  getMe: async () => {
    const response = await apiClient.get("/api/users/me/");
    return response.data;
  }
};
