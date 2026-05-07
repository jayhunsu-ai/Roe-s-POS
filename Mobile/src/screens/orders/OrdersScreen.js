import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { fetchOrders, updateOrderStatus } from '../../redux/slices/orderSlice';

const ORDER_STATUSES = {
  pending: {label: 'Pending', color: '#FF6F00'},
  confirmed: {label: 'Confirmed', color: '#1976D2'},
  preparing: {label: 'Preparing', color: '#FF9800'},
  ready: {label: 'Ready', color: '#4CAF50'},
  completed: {label: 'Completed', color: '#4CAF50'},
  cancelled: {label: 'Cancelled', color: '#F44336'},
};

const OrdersScreen = () => {
  const dispatch = useDispatch();
  const { orders, isLoading, error } = useSelector((state) => state.order);
  const [selectedStatus, setSelectedStatus] = useState(null);

  useEffect(() => {
    dispatch(fetchOrders());
  }, [dispatch]);

  const filteredOrders = useMemo(
    () => orders.filter((order) => !selectedStatus || order.status === selectedStatus),
    [orders, selectedStatus]
  );

  const handleStatusUpdate = (orderId, newStatus) => {
    if (!window.confirm(`Change order status to ${ORDER_STATUSES[newStatus].label}?`)) {
      return;
    }
    dispatch(updateOrderStatus({ orderId, status: newStatus }));
  };

  const getNextStatus = (currentStatus) => {
    const statusFlow = ['pending', 'confirmed', 'preparing', 'ready', 'completed'];
    const currentIndex = statusFlow.indexOf(currentStatus);
    return currentIndex < statusFlow.length - 1 ? statusFlow[currentIndex + 1] : null;
  };

  if (isLoading) {
    return (
      <Stack alignItems="center" sx={{ mt: 10 }} spacing={2}>
        <CircularProgress />
        <Typography color="text.secondary">Loading orders...</Typography>
      </Stack>
    );
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}
      <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', mb: 2 }}>
        {Object.entries(ORDER_STATUSES).map(([key, value]) => (
          <Chip
            key={key}
            label={value.label}
            color={selectedStatus === key ? 'primary' : 'default'}
            onClick={() => setSelectedStatus(selectedStatus === key ? null : key)}
          />
        ))}
      </Stack>

      <Stack spacing={2}>
        {filteredOrders.map((item) => {
          const orderId = item.orderId ?? item.id;
          const createdAt = item.createdAt ?? item.created_at;
          const totalAmount = Number(item.totalAmount ?? item.total_amount ?? 0);
          const status = (item.status ?? 'pending').toLowerCase();
          const statusMeta = ORDER_STATUSES[status] ?? ORDER_STATUSES.pending;
          const nextStatus = getNextStatus(status);
          const customerName = item.customerName ?? item.customer_name ?? 'Walk-in Customer';
          const lineItems = item.items ?? [];
          return (
            <Card key={String(orderId)} sx={{ borderRadius: 2 }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" fontWeight={700}>
                      Order #{item.orderNumber ?? orderId}
                    </Typography>
                    <Typography color="text.secondary">{customerName}</Typography>
                    {createdAt && (
                      <Typography variant="caption" color="text.secondary">
                        {new Date(createdAt).toLocaleString()}
                      </Typography>
                    )}
                  </Box>
                  <Chip
                    label={statusMeta.label}
                    sx={{ bgcolor: statusMeta.color, color: 'white', fontWeight: 700 }}
                  />
                </Stack>

                <Typography variant="subtitle2" sx={{ mb: 1 }}>Items:</Typography>
                <Stack spacing={0.5} sx={{ mb: 2 }}>
                  {lineItems.map((orderItem, index) => (
                    <Typography key={index} variant="body2" color="text.secondary">
                      • {orderItem.quantity}x {orderItem.menuItem?.name ?? orderItem.menu_item?.name ?? 'Item'}
                    </Typography>
                  ))}
                </Stack>

                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="primary">
                    Total: ${totalAmount.toFixed(2)}
                  </Typography>
                  {nextStatus && (
                    <Button
                      variant="contained"
                      onClick={() => handleStatusUpdate(orderId, nextStatus)}
                      sx={{ bgcolor: ORDER_STATUSES[nextStatus].color }}
                    >
                      Mark as {ORDER_STATUSES[nextStatus].label}
                    </Button>
                  )}
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
};

export default OrdersScreen;