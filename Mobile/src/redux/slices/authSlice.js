import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://your-server-ip:8000/api/v1';

const loadStorageValue = (key) => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(key);
};

const loadStorageObject = (key) => {
  if (typeof window === 'undefined') return null;
  const value = window.localStorage.getItem(key);
  return value ? JSON.parse(value) : null;
};

const saveStorageValue = (key, value) => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, value);
};

const removeStorageValue = (key) => {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(key);
};

export const loginWithPin = createAsyncThunk(
  'auth/loginWithPin',
  async ({ pin }, { rejectWithValue }) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/token/`, {
        username: pin,
        password: pin,
      });
      const { access, refresh, user } = response.data;

      saveStorageValue('accessToken', access);
      saveStorageValue('refreshToken', refresh);
      saveStorageValue('authUser', JSON.stringify(user));

      return { access, refresh, user };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed');
    }
  }
);

export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { rejectWithValue }) => {
    try {
      const refresh = loadStorageValue('refreshToken');
      if (!refresh) {
        throw new Error('No refresh token available');
      }

      const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
        refresh,
      });
      const { access } = response.data;

      saveStorageValue('accessToken', access);
      return { access };
    } catch (error) {
      return rejectWithValue('Token refresh failed');
    }
  }
);

export const logout = createAsyncThunk('auth/logout', async () => {
  removeStorageValue('accessToken');
  removeStorageValue('refreshToken');
  removeStorageValue('authUser');
});

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: loadStorageObject('authUser'),
    accessToken: loadStorageValue('accessToken'),
    refreshToken: loadStorageValue('refreshToken'),
    isLoading: false,
    error: null,
    isAuthenticated: !!loadStorageValue('accessToken'),
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setAccessToken: (state, action) => {
      state.accessToken = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginWithPin.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginWithPin.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.accessToken = action.payload.access;
        state.refreshToken = action.payload.refresh;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(loginWithPin.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
        state.isAuthenticated = false;
      })
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.accessToken = action.payload.access;
      })
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.accessToken = null;
        state.refreshToken = null;
        state.isAuthenticated = false;
        state.error = null;
      });
  },
});

export const { clearError } = authSlice.actions;
export default authSlice.reducer;