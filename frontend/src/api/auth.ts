import { apiClient } from "./client";

const MUST_CHANGE_KEY = "must_change_password";

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

    // Remember whether the user must change their password on first login.
    const mustChange = !!response.data?.user?.mustChangePassword;
    localStorage.setItem(MUST_CHANGE_KEY, String(mustChange));

    return response.data;
  },

  // Self-service signup: provision an account from the employee directory.
  // The backend SMSes a temporary password to the employee's registered phone.
  signup: async (employee_id: string) => {
    const response = await apiClient.post("/api/users/signup/", { employee_id });
    return response.data;
  },

  changePassword: async (data: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }) => {
    const response = await apiClient.post("/api/users/change-password/", data);
    // Forced-change requirement (if any) is now satisfied.
    localStorage.setItem(MUST_CHANGE_KEY, "false");
    return response.data;
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem(MUST_CHANGE_KEY);
    window.location.href = "/login";
  },

  isAuthenticated: () => {
    return !!localStorage.getItem("access_token");
  },

  mustChangePassword: () => {
    return localStorage.getItem(MUST_CHANGE_KEY) === "true";
  },

  getMe: async () => {
    const response = await apiClient.get("/api/users/me/");
    return response.data;
  },
};
