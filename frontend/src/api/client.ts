import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to attach access token and handle FormData
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // If the data is FormData, let axios/browser handle the Content-Type (multipart/form-data)
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

const REFRESH_URL = "/api/users/token/refresh/";

const forceLogout = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("must_change_password");
  window.location.href = "/login";
};

// Dedupe concurrent refreshes: many requests can 401 at once, but we only want
// to hit the refresh endpoint a single time and let the rest await that result.
let refreshPromise: Promise<string> | null = null;

const refreshAccessToken = async (): Promise<string> => {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) throw new Error("No refresh token");
  // Use a bare axios call so this request doesn't re-enter the interceptor.
  const { data } = await axios.post(`${apiClient.defaults.baseURL}${REFRESH_URL}`, { refresh });
  const access = data?.access;
  if (!access) throw new Error("No access token in refresh response");
  localStorage.setItem("access_token", access);
  return access;
};

// Response interceptor: on a 401, try a one-time silent refresh + retry before
// giving up and logging the user out.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    const isRefreshCall = original?.url?.includes(REFRESH_URL);
    if (status !== 401 || !original || original._retry || isRefreshCall) {
      if (status === 401 && isRefreshCall) forceLogout();
      return Promise.reject(error);
    }

    original._retry = true;
    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const access = await refreshPromise;
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${access}`;
      return apiClient(original);
    } catch (refreshError) {
      forceLogout();
      return Promise.reject(refreshError);
    }
  }
);
