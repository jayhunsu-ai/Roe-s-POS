import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

const getLocalAccessToken  = () => typeof window !== 'undefined' ? window.localStorage.getItem('accessToken')  : null;
const getLocalRefreshToken = () => typeof window !== 'undefined' ? window.localStorage.getItem('refreshToken') : null;

// ── Clear session and bounce to login ────────────────────────────────────────
const forceLogout = () => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem('accessToken');
  window.localStorage.removeItem('refreshToken');
  // Adjust the path to wherever your login route is
  window.location.href = '/login';
};

const refreshAccessToken = async () => {
  const refresh = getLocalRefreshToken();
  if (!refresh) throw new Error('No refresh token available');

  const response = await axios.post(
    `${API_BASE_URL}/token/refresh/`,
    { refresh },
    {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    }
  );

  const { access } = response.data;
  if (!access) throw new Error('Refresh failed — no access token returned');

  if (typeof window !== 'undefined') {
    window.localStorage.setItem('accessToken', access);
  }
  return access;
};

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => refreshSubscribers.push(callback);
const onRefreshed = (token) => {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
};

// ── Request interceptor ──────────────────────────────────────────────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = getLocalAccessToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ─────────────────────────────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const is401          = error.response?.status === 401;
    const isRefreshRoute = originalRequest?.url?.includes('/token/refresh/');
    const alreadyRetried = originalRequest?._retry;

    // If the refresh endpoint itself returned 401 → session is dead
    if (is401 && isRefreshRoute) {
      forceLogout();
      return Promise.reject(error);
    }

    // Normal 401 on any other route → try to refresh
    if (is401 && !alreadyRetried) {
      originalRequest._retry = true;

      if (isRefreshing) {
        // Queue this request until the ongoing refresh completes
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(async (token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            try   { resolve(await apiClient(originalRequest)); }
            catch (err) { reject(err); }
          });
        });
      }

      isRefreshing = true;
      try {
        const newToken = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        onRefreshed(newToken);
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh attempt failed — kill the session
        refreshSubscribers = [];
        forceLogout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
