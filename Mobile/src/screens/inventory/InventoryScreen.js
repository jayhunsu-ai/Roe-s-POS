import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInventory, updateInventoryItem } from '../../redux/slices/inventorySlice';

const InventoryScreen = () => {
  const dispatch = useDispatch();
  const { items, isLoading, error } = useSelector((state) => state.inventory);
  const [selectedItem, setSelectedItem] = useState(null);
  const [newStock, setNewStock] = useState('');
  const [dialogVisible, setDialogVisible] = useState(false);

  useEffect(() => {
    dispatch(fetchInventory());
  }, [dispatch]);

  const handleUpdateStock = (item) => {
    setSelectedItem(item);
    setNewStock(String(item.current_stock ?? item.quantityInStock ?? 0));
    setDialogVisible(true);
  };

  const handleConfirmUpdate = () => {
    const stockValue = parseFloat(newStock);
    if (isNaN(stockValue) || stockValue < 0) {
      return;
    }

    dispatch(updateInventoryItem({
      itemId: selectedItem.id ?? selectedItem.inventoryItemId,
      data: { current_stock: stockValue, quantityInStock: stockValue },
    }));

    setDialogVisible(false);
    setSelectedItem(null);
    setNewStock('');
  };

  const getStockStatus = (item) => {
    const current = Number(item.current_stock ?? item.quantityInStock ?? 0);
    const minimum = Number(item.min_stock_level ?? item.lowStockThreshold ?? 1);
    const percentage = minimum > 0 ? (current / minimum) * 100 : 100;
    if (percentage <= 25) return {status: 'Low Stock', color: '#F44336'};
    if (percentage <= 50) return {status: 'Medium Stock', color: '#FF9800'};
    return {status: 'Good Stock', color: '#4CAF50'};
  };

  if (isLoading) {
    return (
      <Stack alignItems="center" sx={{ mt: 10 }} spacing={2}>
        <CircularProgress />
        <Typography color="text.secondary">Loading inventory...</Typography>
      </Stack>
    );
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}
      <Stack spacing={2}>
        {items.map((item) => {
          const stockStatus = getStockStatus(item);
          const current = Number(item.current_stock ?? item.quantityInStock ?? 0);
          const minimum = Number(item.min_stock_level ?? item.lowStockThreshold ?? 0);
          return (
            <Card
              key={String(item.id ?? item.inventoryItemId)}
              sx={{ borderRadius: 2, cursor: 'pointer' }}
              onClick={() => handleUpdateStock(item)}
            >
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="h6" fontWeight={700}>{item.name}</Typography>
                  <Chip label={stockStatus.status} sx={{ bgcolor: stockStatus.color, color: 'white' }} />
                </Stack>
                <Typography variant="h4" color="primary" fontWeight={700}>
                  {current} {item.unit}
                </Typography>
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                  Min Level: {minimum} {item.unit}
                </Typography>
                <Button variant="contained" onClick={(e) => { e.stopPropagation(); handleUpdateStock(item); }}>
                  Update Stock
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      <Dialog open={dialogVisible} onClose={() => setDialogVisible(false)} fullWidth maxWidth="sm">
        <DialogTitle>Update Stock Level</DialogTitle>
        <DialogContent>
          <Typography sx={{ mb: 2, fontWeight: 700 }}>{selectedItem?.name}</Typography>
          <TextField
            label={`Stock Quantity (${selectedItem?.unit ?? 'units'})`}
            value={newStock}
            onChange={(e) => setNewStock(e.target.value)}
            type="number"
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogVisible(false)}>Cancel</Button>
          <Button onClick={handleConfirmUpdate} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default InventoryScreen;