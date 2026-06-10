import { apiClient } from "./client";

const MUST_CHANGE_KEY = "must_change_password";

// Persist tokens + the forced-password-change flag from a successful auth
// response (shared by password login and OTP verification).
const persistSession = (data: any) => {
  const { access, refresh } = data || {};
  if (access) localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
  const mustChange = !!data?.user?.mustChangePassword;
  localStorage.setItem(MUST_CHANGE_KEY, String(mustChange));
};

export const authService = {
  login: async (employee_id: string, password: string) => {
    // The backend uses employee_id as the primary identifier instead of username
    const response = await apiClient.post("/api/users/token/", {
      employee_id,
      password,
    });

    // When OTP is enabled the backend returns { otp_required, user_id, phone_hint }
    // (HTTP 200, no tokens). In that case we don't persist a session — the caller
    // must complete verifyOtp(). Otherwise persist the issued tokens.
    if (!response.data?.otp_required) {
      persistSession(response.data);
    }

    return response.data;
  },

  // Complete an OTP challenge started by login(): exchange the code for tokens.
  verifyOtp: async (user_id: string, otp: string) => {
    const response = await apiClient.post("/api/users/otp-verify/", {
      user_id,
      otp,
    });
    persistSession(response.data);
    return response.data;
  },

  // Resend the login OTP to the user's registered phone.
  resendOtp: async (user_id: string) => {
    const response = await apiClient.post("/api/users/otp-resend/", { user_id });
    return response.data;
  },

  // Self-service signup step 1: request an OTP to the employee's registered phone.
  signup: async (employee_id: string) => {
    const response = await apiClient.post("/api/users/signup/", { employee_id });
    return response.data;
  },

  // Self-service signup step 2: verify the OTP and set the chosen password.
  // Creates the account; the user then logs in normally.
  signupVerify: async (employee_id: string, otp: string, password: string) => {
    const response = await apiClient.post("/api/users/signup/verify/", {
      employee_id,
      otp,
      password,
    });
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
