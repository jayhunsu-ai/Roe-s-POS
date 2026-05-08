import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  IconButton,
  InputAdornment,
  TextField,
  Typography,
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { clearError, loginWithPin } from '../../redux/slices/authSlice';

const LoginScreen = () => {
  const [email, setEmail] = useState('');
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [showError, setShowError] = useState(false);

  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { isLoading, error, isAuthenticated } = useSelector((state) => state.auth);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/menu');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (error) {
      setShowError(true);
      const timer = setTimeout(() => {
        setShowError(false);
        dispatch(clearError());
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error, dispatch]);

  const handleLogin = (e) => {
    e?.preventDefault();
    if (!email.trim() || !pin.trim()) return;
    dispatch(loginWithPin({ email: email.trim(), pin: pin.trim() }));
  };

  const isFormValid = email.trim().length > 0 && pin.trim().length >= 6;

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: '#1976D2',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
      }}
    >
      <Box sx={{ width: '100%', maxWidth: 420 }}>
        {/* Header */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h4" color="white" fontWeight={300}>
            Welcome to
          </Typography>
          <Typography variant="h3" color="white" fontWeight={700}>
            Roe&apos;s POS
          </Typography>
          <Typography sx={{ color: 'rgba(255,255,255,0.8)', mt: 0.5 }}>
            Sign in to get started
          </Typography>
        </Box>

        {/* Card */}
        <Card sx={{ borderRadius: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 3 }}>
              Staff Login
            </Typography>

            {showError && error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {/* Email */}
            <TextField
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
              fullWidth
              autoComplete="email"
              autoFocus
              sx={{ mb: 2 }}
            />

            {/* PIN / Password */}
            <TextField
              label="PIN"
              type={showPin ? 'text' : 'password'}
              value={pin}
              onChange={(e) => {
                const val = e.target.value;
                // Allow only digits, max 6 chars
                if (/^\d{0,6}$/.test(val)) setPin(val);
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
              fullWidth
              inputProps={{ maxLength: 6, inputMode: 'numeric' }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPin((prev) => !prev)}
                      edge="end"
                      aria-label={showPin ? 'Hide PIN' : 'Show PIN'}
                    >
                      {showPin ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              helperText="Enter your 6-digit PIN"
              sx={{ mb: 3 }}
            />

            {/* Submit */}
            <Button
              variant="contained"
              fullWidth
              onClick={handleLogin}
              disabled={isLoading || !isFormValid}
              sx={{ py: 1.5, borderRadius: 2, fontSize: 16 }}
            >
              {isLoading ? <CircularProgress size={22} color="inherit" /> : 'Login'}
            </Button>
          </CardContent>
        </Card>

        <Typography textAlign="center" sx={{ color: 'rgba(255,255,255,0.7)', mt: 2 }}>
          Ask your manager if you don&apos;t know your PIN
        </Typography>
      </Box>
    </Box>
  );
};

export default LoginScreen;
