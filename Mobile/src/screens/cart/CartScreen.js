import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { createOrder } from '../../redux/slices/orderSlice';
import { removeFromCart, updateCartItemQuantity } from '../../redux/slices/orderSlice';

const CartScreen = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { cart, isLoading } = useSelector((state) => state.order);
  const [customerName, setCustomerName] = useState('');

  const getTotalItems = () => {
    return cart.reduce((total, item) => total + item.quantity, 0);
  };

  const getTotalPrice = () => {
    return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
  };

  const handleQuantityChange = (item, change) => {
    const newQuantity = item.quantity + change;
    if (newQuantity <= 0) {
      dispatch(removeFromCart(item.id));
    } else {
      dispatch(updateCartItemQuantity({itemId: item.id, quantity: newQuantity}));
    }
  };

  const [showHoldDialog, setShowHoldDialog] = useState(false);
  const [holdCustomerName, setHoldCustomerName] = useState('');

  const handleCreateOrder = () => {
    if (cart.length === 0) {
      return;
    }

    const orderData = {
      customerName: customerName.trim() || null,
      paymentStatus: 'Paid',
      status: 'Completed',
      items: cart.map(item => ({
        menuItem: item.id,
        quantity: item.quantity,
        unitPrice: item.price,
      })),
    };

    dispatch(createOrder(orderData));
    alert('Order created successfully');
    navigate('/menu');
  };

  const handleHoldPayment = () => {
    if (cart.length === 0) {
      return;
    }
    
    if (!holdCustomerName.trim()) {
      alert('Please enter customer name for hold payment');
      return;
    }

    const orderData = {
      customerName: holdCustomerName.trim(),
      paymentStatus: 'Unpaid',
      status: 'Pending', // Ensure order is pending
      items: cart.map(item => ({
        menuItem: item.id,
        quantity: item.quantity,
        unitPrice: item.price,
      })),
    };

    dispatch(createOrder(orderData));
    alert('Order placed on hold - payment pending');
    setShowHoldDialog(false);
    setHoldCustomerName('');
    navigate('/menu');
  };

  if (cart.length === 0) {
    return (
      <Stack alignItems="center" spacing={2} sx={{ mt: 10 }}>
        <Typography variant="h4" color="text.secondary">Your cart is empty</Typography>
        <Typography color="text.secondary">Add some delicious items from the menu</Typography>
        <Button variant="contained" onClick={() => navigate('/menu')}>
          Browse Menu
        </Button>
      </Stack>
    );
  }

  return (
    <Box>
      <Stack spacing={2} sx={{ mb: 3 }}>
        {cart.map((item) => (
          <Card key={String(item.id)} sx={{ borderRadius: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography fontWeight={700}>{item.name}</Typography>
                  <Typography color="text.secondary">${Number(item.price).toFixed(2)} each</Typography>
                </Box>

                <Stack direction="row" spacing={1} alignItems="center">
                  <Button variant="outlined" onClick={() => handleQuantityChange(item, -1)}>-</Button>
                  <Typography sx={{ minWidth: 24, textAlign: 'center' }}>{item.quantity}</Typography>
                  <Button variant="outlined" onClick={() => handleQuantityChange(item, 1)}>+</Button>
                </Stack>

                <Typography fontWeight={700} color="primary.main">
                  ${(Number(item.price) * item.quantity).toFixed(2)}
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Card sx={{ borderRadius: 2 }}>
        <CardContent>
          <TextField
            label="Customer Name (Optional)"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            fullWidth
            sx={{ mb: 2 }}
          />

          <Stack direction="row" justifyContent="space-between" sx={{ mb: 2 }}>
            <Typography color="text.secondary">
              {getTotalItems()} item{getTotalItems() > 1 ? 's' : ''}
            </Typography>
            <Typography variant="h6" color="primary.main">
              Total: ${getTotalPrice().toFixed(2)}
            </Typography>
          </Stack>

          <Stack direction="row" spacing={1}>
            <Button 
              variant="outlined" 
              fullWidth 
              onClick={() => setShowHoldDialog(true)} 
              disabled={isLoading}
              sx={{ flex: 1 }}
            >
              Hold Payment
            </Button>
            <Button 
              variant="contained" 
              fullWidth 
              onClick={handleCreateOrder} 
              disabled={isLoading}
              sx={{ flex: 1 }}
            >
              {isLoading ? <CircularProgress size={20} color="inherit" /> : 'Complete Payment'}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Hold Payment Dialog */}
      <Dialog open={showHoldDialog} onClose={() => setShowHoldDialog(false)}>
        <DialogTitle>Hold Payment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Customer Name"
            fullWidth
            variant="outlined"
            value={holdCustomerName}
            onChange={(e) => setHoldCustomerName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHoldDialog(false)}>Cancel</Button>
          <Button onClick={handleHoldPayment} variant="contained">
            Place on Hold
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CartScreen;