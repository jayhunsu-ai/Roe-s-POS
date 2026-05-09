import React, { useEffect } from 'react';
import { Provider, useSelector } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { store } from './src/redux/store';
import { theme } from './src/theme/theme';

// Screens
import LoginScreen from './src/screens/auth/LoginScreen';
import MenuScreen from './src/screens/menu/MenuScreen';
import OrdersScreen from './src/screens/orders/OrdersScreen';
import InventoryScreen from './src/screens/inventory/InventoryScreen';
import ProfileScreen from './src/screens/profile/ProfileScreen';
import CartScreen from './src/screens/cart/CartScreen';
import MainLayout from './src/navigation/MainLayout';
import IMDashboardScreen from './src/screens/im/IMDashboardScreen';
import StoreScreen from './src/screens/store/StoreScreen';

// ── WebSocket notification listener ──────────────────────────────────────────
const NotificationListener = () => {
  const accessToken = useSelector((state) => state.auth.accessToken);
  useEffect(() => {
    if (!accessToken) return;
    const base   = process.env.REACT_APP_API_BASE_URL || 'https://roe-s-pos-production.up.railway.app/api/v1';
    const wsBase = base.replace(/^http/, 'ws').replace(/\/$/, '');
    const socket = new WebSocket(`${wsBase}/ws/notifications/?token=${accessToken}`);
    socket.onmessage = (event) => {
      try { console.log('Notification:', JSON.parse(event.data)); } catch (e) {}
    };
    return () => socket.close();
  }, [accessToken]);
  return null;
};

// ── Redirect unauthenticated users to login ───────────────────────────────────
const RequireAuth = ({ children, allowedRoles }) => {
  const { isAuthenticated, user } = useSelector((state) => state.auth);
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (allowedRoles && user?.role && !allowedRoles.includes(user.role)) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

// ── After login, send each role to their dashboard ───────────────────────────
const RoleRedirect = () => {
  const { isAuthenticated, user } = useSelector((state) => state.auth);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.role === 'InventoryManager') return <Navigate to="/im/dashboard" replace />;
  return <Navigate to="/menu" replace />;
};

const AppRoutes = () => (
  <Routes>
    {/* Public */}
    <Route path="/login" element={<LoginScreen />} />

    {/* Root → role-based redirect */}
    <Route path="/" element={<RoleRedirect />} />

    {/* ── Inventory Manager ── */}
    <Route path="/im/dashboard" element={
      <RequireAuth allowedRoles={['InventoryManager', 'Administrator']}>
        <IMDashboardScreen />
      </RequireAuth>
    } />
    <Route path="/store" element={
      <RequireAuth allowedRoles={['InventoryManager', 'Administrator']}>
        <StoreScreen />
      </RequireAuth>
    } />

    {/* ── Clerk / Admin (MainLayout with bottom nav) ── */}
    <Route path="/*" element={
      <RequireAuth allowedRoles={['Clerk', 'Administrator', 'Kitchen', 'InventoryManager']}>
        <MainLayout />
      </RequireAuth>
    }>
      <Route path="menu"      element={<MenuScreen />} />
      <Route path="orders"    element={<OrdersScreen />} />
      <Route path="inventory" element={<InventoryScreen />} />
      <Route path="profile"   element={<ProfileScreen />} />
      <Route path="cart"      element={<CartScreen />} />
      <Route index            element={<RoleRedirect />} />
    </Route>

    {/* Fallback */}
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>
);

const App = () => (
  <Provider store={store}>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <NotificationListener />
      <Router>
        <AppRoutes />
      </Router>
    </ThemeProvider>
  </Provider>
);

export default App;
