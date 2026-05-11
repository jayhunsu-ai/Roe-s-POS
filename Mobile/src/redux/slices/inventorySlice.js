import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import apiClient from '../../api/axiosClient';

export const fetchInventory = createAsyncThunk(
  'inventory/fetchInventory',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get('/inventory/items/');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to fetch inventory');
    }
  }
);

export const createInventoryItem = createAsyncThunk(
  'inventory/createInventoryItem',
  async (data, { rejectWithValue }) => {
    try {
      const response = await apiClient.post('/inventory/items/', data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to create item');
    }
  }
);

export const updateInventoryItem = createAsyncThunk(
  'inventory/updateInventoryItem',
  async ({ itemId, data }, { rejectWithValue }) => {
    try {
      const response = await apiClient.patch(`/inventory/items/${itemId}/`, data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to update inventory');
    }
  }
);

export const deleteInventoryItem = createAsyncThunk(
  'inventory/deleteInventoryItem',
  async (itemId, { rejectWithValue }) => {
    try {
      await apiClient.delete(`/inventory/items/${itemId}/`);
      return itemId;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Failed to delete item');
    }
  }
);

const inventorySlice = createSlice({
  name: 'inventory',
  initialState: {
    items: [],
    isLoading: false,
    error: null,
  },
  reducers: {
    clearInventoryError: (state) => { state.error = null; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInventory.pending,   (state) => { state.isLoading = true; state.error = null; })
      .addCase(fetchInventory.fulfilled, (state, action) => { state.isLoading = false; state.items = action.payload; })
      .addCase(fetchInventory.rejected,  (state, action) => { state.isLoading = false; state.error = action.payload; })

      .addCase(createInventoryItem.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
      })

      .addCase(updateInventoryItem.fulfilled, (state, action) => {
        const idx = state.items.findIndex(i => i.id === action.payload.id);
        if (idx !== -1) state.items[idx] = action.payload;
      })

      .addCase(deleteInventoryItem.fulfilled, (state, action) => {
        state.items = state.items.filter(i => i.id !== action.payload);
      });
  },
});

export const { clearInventoryError } = inventorySlice.actions;
export default inventorySlice.reducer;
