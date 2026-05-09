import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import apiClient from '../../api/axiosClient';

// ── Thunks ────────────────────────────────────────────────────────────────────

export const fetchStoreItems = createAsyncThunk(
  'store/fetchItems',
  async (_, { rejectWithValue }) => {
    try {
      const res = await apiClient.get('/store/items/?active_only=true');
      return res.data?.results ?? res.data;
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || 'Failed to load store items');
    }
  }
);

export const createStoreItem = createAsyncThunk(
  'store/createItem',
  async (data, { rejectWithValue }) => {
    try {
      const res = await apiClient.post('/store/items/', data);
      return res.data;
    } catch (e) {
      return rejectWithValue(e.response?.data || 'Failed to create item');
    }
  }
);

export const updateStoreItem = createAsyncThunk(
  'store/updateItem',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const res = await apiClient.patch(`/store/items/${id}/`, data);
      return res.data;
    } catch (e) {
      return rejectWithValue(e.response?.data || 'Failed to update item');
    }
  }
);

export const logStoreTransaction = createAsyncThunk(
  'store/logTransaction',
  async ({ id, transaction_type, quantity, note }, { rejectWithValue }) => {
    try {
      const res = await apiClient.post(`/store/items/${id}/transact/`, {
        transaction_type,
        quantity,
        note: note || '',
      });
      return { itemId: id, transaction: res.data };
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || 'Transaction failed');
    }
  }
);

// ── Slice ─────────────────────────────────────────────────────────────────────

const storeSlice = createSlice({
  name: 'store',
  initialState: {
    items: [],
    isLoading: false,
    isTransacting: false,
    error: null,
    transactionError: null,
  },
  reducers: {
    clearError: (state) => { state.error = null; state.transactionError = null; },
  },
  extraReducers: (builder) => {
    builder
      // fetch
      .addCase(fetchStoreItems.pending,   (state) => { state.isLoading = true; state.error = null; })
      .addCase(fetchStoreItems.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = Array.isArray(action.payload) ? action.payload : [];
      })
      .addCase(fetchStoreItems.rejected,  (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // create
      .addCase(createStoreItem.fulfilled, (state, action) => {
        state.items.push(action.payload);
      })
      // update
      .addCase(updateStoreItem.fulfilled, (state, action) => {
        const idx = state.items.findIndex(i => i.id === action.payload.id);
        if (idx !== -1) state.items[idx] = action.payload;
      })
      // transact — optimistically update current_quantity from response
      .addCase(logStoreTransaction.pending,   (state) => { state.isTransacting = true; state.transactionError = null; })
      .addCase(logStoreTransaction.fulfilled, (state, action) => {
        state.isTransacting = false;
        const { itemId, transaction } = action.payload;
        const item = state.items.find(i => i.id === itemId);
        if (item) item.current_quantity = transaction.quantity_after;
      })
      .addCase(logStoreTransaction.rejected,  (state, action) => {
        state.isTransacting = false;
        state.transactionError = action.payload;
      });
  },
});

export const { clearError } = storeSlice.actions;
export default storeSlice.reducer;
