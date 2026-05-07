import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL 

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

const getLocalAccessToken = () => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem('accessToken');
};

const getLocalRefreshToken = () => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem('refreshToken');
};

const refreshAccessToken = async () => {
  const refresh = getLocalRefreshToken();
  if (!refresh) {
    throw new Error('No refresh token available');
  }
  const response = await axios.post(
    `${API_BASE_URL}/token/refresh/`,
    { refresh },
    {
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    }
  );

  const { access } = response.data;
  if (!access) {
    throw new Error('Refresh failed');
  }

  if (typeof window !== 'undefined') {
    window.localStorage.setItem('accessToken', access);
  }

  return access;
};

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onRefreshed = (token) => {
  refreshSubscribers.forEach((callback) => callback(token));
  refreshSubscribers = [];
};

apiClient.interceptors.request.use(
  (config) => {
    const token = getLocalAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/token/refresh/')
    ) {
      originalRequest._retry = true;
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(async (token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            try {
              resolve(await apiClient(originalRequest));
            } catch (err) {
              reject(err);
            }
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
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
