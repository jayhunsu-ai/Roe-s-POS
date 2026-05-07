import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider, useSelector } from 'react-redux';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { store } from './redux/store';
import { theme } from './theme/theme';

// Screens
import LoginScreen from './screens/auth/LoginScreen';
import MenuScreen from './screens/menu/MenuScreen';
import CartScreen from './screens/cart/CartScreen';
import InventoryScreen from './screens/inventory/InventoryScreen';
import OrdersScreen from './screens/orders/OrdersScreen';
import ProfileScreen from './screens/profile/ProfileScreen';

const NotificationListener = () => {
  const accessToken = useSelector((state) => state.auth.accessToken);

  useEffect(() => {
    if (!accessToken) return;

    const base = process.env.REACT_APP_API_BASE_URL || 'https://roe-s-pos-production.up.railway.app/api/v1';
    const wsBase = base.replace(/^http/, 'ws').replace(/\/$/, '');
    const socketUrl = `${wsBase}/ws/notifications/?token=${accessToken}`;
    const socket = new WebSocket(socketUrl);

    socket.onopen = () => {
      console.log('WebSocket connected to notifications');
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        console.log('Realtime notification:', payload);
      } catch (err) {
        console.error('Failed to parse websocket event', err);
      }
    };

    socket.onerror = (event) => {
      console.error('WebSocket error', event);
    };

    socket.onclose = (event) => {
      console.log('WebSocket closed', event.code, event.reason);
    };

    return () => {
      socket.close();
    };
  }, [accessToken]);

  return null;
};

const App = () => {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <NotificationListener />
        <Router>
          <Routes>
            <Route path="/" element={<LoginScreen />} />
            <Route path="/menu" element={<MenuScreen />} />
            <Route path="/cart" element={<CartScreen />} />
            <Route path="/inventory" element={<InventoryScreen />} />
            <Route path="/orders" element={<OrdersScreen />} />
            <Route path="/profile" element={<ProfileScreen />} />
          </Routes>
        </Router>
      </ThemeProvider>
    </Provider>
  );
};

export default App;