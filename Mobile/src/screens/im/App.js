import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider, useSelector } from 'react-redux';
import { ThemeProvider } from '@mui/material/styles';
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
import IMDashboardScreen from './screens/im/IMDashboardScreen';
import StoreScreen from './screens/store/StoreScreen';

// ── Role-based protected route ────────────────────────────────────────────────
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, user } = useSelector((state) => state.auth);
  if (!isAuthenticated) return <Navigate to="/" replace />;
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
};

// ── After login, redirect based on role ──────────────────────────────────────
const RoleRedirect = () => {
  const { isAuthenticated, user } = useSelector((state) => state.auth);
  if (!isAuthenticated) return <LoginScreen />;
  if (user?.role === 'InventoryManager') return <Navigate to="/im/dashboard" replace />;
  if (user?.role === 'Administrator')    return <Navigate to="/menu" replace />;
  if (user?.role === 'Clerk')            return <Navigate to="/menu" replace />;
  return <LoginScreen />;
};

// ── WebSocket notification listener ──────────────────────────────────────────
const NotificationListener = () => {
  const accessToken = useSelector((state) => state.auth.accessToken);
  useEffect(() => {
    if (!accessToken) return;
    const base    = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/v1';
    const wsBase  = base.replace(/^http/, 'ws').replace(/\/$/, '');
    const socket  = new WebSocket(`${wsBase}/ws/notifications/?token=${accessToken}`);
    socket.onmessage = (event) => {
      try { console.log('Notification:', JSON.parse(event.data)); }
      catch (e) { /* noop */ }
    };
    return () => socket.close();
  }, [accessToken]);
  return null;
};

// ── App ───────────────────────────────────────────────────────────────────────
const App = () => (
  <Provider store={store}>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NotificationListener />
      <Router>
        <Routes>
          {/* Public */}
          <Route path="/" element={<RoleRedirect />} />

          {/* Inventory Manager routes */}
          <Route path="/im/dashboard" element={
            <ProtectedRoute allowedRoles={['InventoryManager', 'Administrator']}>
              <IMDashboardScreen />
            </ProtectedRoute>
          } />
          <Route path="/inventory" element={
            <ProtectedRoute allowedRoles={['InventoryManager', 'Administrator']}>
              <InventoryScreen />
            </ProtectedRoute>
          } />
          <Route path="/store" element={
            <ProtectedRoute allowedRoles={['InventoryManager', 'Administrator']}>
              <StoreScreen />
            </ProtectedRoute>
          } />

          {/* Clerk / Admin routes */}
          <Route path="/menu" element={
            <ProtectedRoute allowedRoles={['Clerk', 'Administrator', 'Kitchen']}>
              <MenuScreen />
            </ProtectedRoute>
          } />
          <Route path="/cart" element={
            <ProtectedRoute>
              <CartScreen />
            </ProtectedRoute>
          } />
          <Route path="/orders" element={
            <ProtectedRoute>
              <OrdersScreen />
            </ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute>
              <ProfileScreen />
            </ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  </Provider>
);

export default App;
