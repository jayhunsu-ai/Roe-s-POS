import React from 'react';
import { Provider, useSelector } from 'react-redux';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { store } from './src/redux/store';
import LoginScreen from './src/screens/auth/LoginScreen';
import MenuScreen from './src/screens/menu/MenuScreen';
import OrdersScreen from './src/screens/orders/OrdersScreen';
import InventoryScreen from './src/screens/inventory/InventoryScreen';
import ProfileScreen from './src/screens/profile/ProfileScreen';
import CartScreen from './src/screens/cart/CartScreen';
import MainLayout from './src/navigation/MainLayout';
import { theme } from './src/theme/theme';

const RequireAuth = ({ children }) => {
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

const AppRoutes = () => (
  <Routes>
    <Route path="/login" element={<LoginScreen />} />
    <Route
      path="/*"
      element={
        <RequireAuth>
          <MainLayout />
        </RequireAuth>
      }
    >
      <Route path="menu" element={<MenuScreen />} />
      <Route path="orders" element={<OrdersScreen />} />
      <Route path="inventory" element={<InventoryScreen />} />
      <Route path="profile" element={<ProfileScreen />} />
      <Route path="cart" element={<CartScreen />} />
      <Route index element={<Navigate to="menu" replace />} />
    </Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>
);

const App = () => {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AppRoutes />
        </Router>
      </ThemeProvider>
    </Provider>
  );
};

export default App;