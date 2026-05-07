import React from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import BottomNavigation from '@mui/material/BottomNavigation';
import BottomNavigationAction from '@mui/material/BottomNavigationAction';
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu';
import ListAltIcon from '@mui/icons-material/ListAlt';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import PersonIcon from '@mui/icons-material/Person';
import Avatar from '@mui/material/Avatar';

const navItems = [
  { label: 'Order', value: '/menu', icon: <RestaurantMenuIcon /> },
  { label: 'Orders', value: '/orders', icon: <ListAltIcon /> },
  { label: 'Inventory', value: '/inventory', icon: <Inventory2Icon /> },
  { label: 'Profile', value: '/profile', icon: <PersonIcon /> },
];

const MainLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useSelector((state) => state.auth.user);
  const value = navItems.find((item) => location.pathname.startsWith(item.value))?.value || '/menu';

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <AppBar position="fixed" color="primary" elevation={3}>
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Typography variant="h6" component="div">
            Roe's POS Staff Web App
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Avatar sx={{ bgcolor: '#ffffff', color: '#1976D2', fontWeight: 700, width: 38, height: 38 }}>
              {user ? `${user.first_name?.charAt(0) || 'U'}${user.last_name?.charAt(0) || ''}` : 'U'}
            </Avatar>
            <Box>
              <Typography variant="subtitle2" color="inherit">
                {user ? `${user.first_name} ${user.last_name}` : 'Staff'}
              </Typography>
              <Typography variant="caption" color="inherit">
                {user?.role ? user.role.toUpperCase() : 'STAFF'}
              </Typography>
            </Box>
          </Box>
        </Toolbar>
      </AppBar>

      <Box sx={{ pt: 10, pb: 9, px: { xs: 2, md: 4 } }}>
        <Outlet />
      </Box>

      <Paper
        sx={{ position: 'fixed', bottom: 0, left: 0, right: 0 }}
        elevation={8}
      >
        <BottomNavigation
          showLabels
          value={value}
          onChange={(_, newValue) => navigate(newValue)}
        >
          {navItems.map((item) => (
            <BottomNavigationAction
              key={item.value}
              label={item.label}
              value={item.value}
              icon={item.icon}
            />
          ))}
        </BottomNavigation>
      </Paper>
    </Box>
  );
};

export default MainLayout;
