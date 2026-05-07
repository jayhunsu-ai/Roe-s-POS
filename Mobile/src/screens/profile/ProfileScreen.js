import React from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Stack,
  Typography,
  Avatar,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from '../../redux/slices/authSlice';

const ProfileScreen = () => {
  const dispatch = useDispatch();
  const user = useSelector((state) => state.auth.user);

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to logout?')) {
      dispatch(logout());
    }
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const getRoleDisplay = (role) => {
    const roles = {
      admin: 'Administrator',
      manager: 'Manager',
      staff: 'Staff Member',
    };
    return roles[role] || role;
  };

  const firstName = user?.first_name || user?.staffName?.split(' ')[0] || 'Staff';
  const lastName = user?.last_name || user?.staffName?.split(' ').slice(1).join(' ') || '';
  const role = user?.role || 'staff';
  const fullName = `${firstName} ${lastName}`.trim();

  return (
    <Box>
      <Box
        sx={{
          textAlign: 'center',
          p: 4,
          borderRadius: 3,
          color: 'white',
          backgroundColor: 'primary.main',
          mb: 3,
        }}
      >
        <Avatar sx={{ width: 92, height: 92, bgcolor: 'rgba(255,255,255,0.25)', mx: 'auto', mb: 2 }}>
          {getInitials(fullName)}
        </Avatar>
        <Typography variant="h5" fontWeight={700}>{fullName || 'Staff Member'}</Typography>
        <Typography sx={{ opacity: 0.9 }}>{getRoleDisplay(role)}</Typography>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <Card>
            <CardContent>
              <Typography variant="h6">Today&apos;s Sales</Typography>
              <Typography color="text.secondary">View reports</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6}>
          <Card>
            <CardContent>
              <Typography variant="h6">Clock In/Out</Typography>
              <Typography color="text.secondary">Time tracking</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={2}>
            <Typography>Change PIN</Typography>
            <Typography>Notifications</Typography>
            <Typography>Help &amp; Support</Typography>
            <Typography>About</Typography>
          </Stack>
        </CardContent>
      </Card>

      <Button color="error" variant="contained" fullWidth onClick={handleLogout}>
        Logout
      </Button>
    </Box>
  );
};

export default ProfileScreen;