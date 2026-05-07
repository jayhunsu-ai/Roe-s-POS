import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Fab,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { addToCart } from '../../redux/slices/orderSlice';
import { fetchCategories, fetchMenuItems } from '../../redux/slices/menuSlice';

const MenuScreen = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { items, categories, isLoading, error } = useSelector((state) => state.menu);
  const cart = useSelector((state) => state.order.cart);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    dispatch(fetchMenuItems());
    dispatch(fetchCategories());
  }, [dispatch]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const categoryId = item.category?.categoryId ?? item.category;
    const itemName = item.name ?? '';
    const itemDesc = item.description ?? '';
    const isAvailable = item.isAvailable ?? item.is_available ?? true;
    const itemId = item.menuItemId ?? item.id;
    if (!itemId) return false;

    const matchesCategory = !selectedCategory || categoryId === selectedCategory;
    const matchesSearch = !searchQuery ||
      itemName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      itemDesc.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch && isAvailable;
  }), [items, searchQuery, selectedCategory]);

  const handleAddToCart = (item) => {
    const normalized = {
      ...item,
      id: item.menuItemId ?? item.id,
      price: Number(item.price ?? 0),
      name: item.name ?? 'Unnamed item',
    };
    dispatch(addToCart(normalized));
  };

  const getCartItemCount = (itemId) => {
    const cartItem = cart.find((item) => item.id === itemId);
    return cartItem ? cartItem.quantity : 0;
  };

  if (isLoading) {
    return (
      <Stack alignItems="center" sx={{ mt: 10 }} spacing={2}>
        <CircularProgress />
        <Typography color="text.secondary">Loading menu...</Typography>
      </Stack>
    );
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}

      <TextField
        placeholder="Search menu items..."
        onChange={(e) => setSearchQuery(e.target.value)}
        value={searchQuery}
        fullWidth
        sx={{ mb: 2 }}
      />

      <Stack direction="row" spacing={1} sx={{ overflowX: 'auto', pb: 1, mb: 2 }}>
        {categories.map((item) => {
          const categoryId = item.categoryId ?? item.id;
          return (
            <Chip
              key={String(categoryId)}
              label={item.name}
              color={selectedCategory === categoryId ? 'primary' : 'default'}
              onClick={() => setSelectedCategory(selectedCategory === categoryId ? null : categoryId)}
            />
          );
        })}
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
          gap: 2,
        }}
      >
        {filteredItems.map((item) => {
          const itemId = item.menuItemId ?? item.id;
          const price = Number(item.price ?? 0);
          const qty = getCartItemCount(itemId);
          return (
            <Card key={String(itemId)} sx={{ borderRadius: 2 }}>
              <CardContent>
                <Typography variant="h6" fontWeight={700}>{item.name}</Typography>
                {item.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {item.description}
                  </Typography>
                )}
                <Typography variant="h6" color="primary" sx={{ mb: 2 }}>
                  ${price.toFixed(2)}
                </Typography>
                <Button fullWidth variant="contained" onClick={() => handleAddToCart(item)}>
                  Add {qty > 0 ? `(${qty})` : ''}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </Box>

      {cart.length > 0 && (
        <Fab
          variant="extended"
          color="primary"
          onClick={() => navigate('/cart')}
          sx={{ position: 'fixed', right: 24, bottom: 24 }}
        >
          <ShoppingCartIcon sx={{ mr: 1 }} />
          {cart.length} item{cart.length > 1 ? 's' : ''}
        </Fab>
      )}
    </Box>
  );
};

export default MenuScreen;