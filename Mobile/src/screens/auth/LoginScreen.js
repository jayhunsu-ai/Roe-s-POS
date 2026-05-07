import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Typography,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { clearError, loginWithPin } from '../../redux/slices/authSlice';

const LoginScreen = () => {
  const [pin, setPin] = useState('');
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

  const handleLogin = async () => {
    if (!pin.trim()) {
      return;
    }
    if (pin.length < 4) {
      return;
    }
    dispatch(loginWithPin({ pin: pin.trim() }));
  };

  const handleNumberPress = (number) => {
    if (pin.length < 6) {
      setPin((prev) => prev + number);
    }
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
  };

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
      <Box sx={{ width: '100%', maxWidth: 480 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h4" color="white" fontWeight={300}>
            Welcome to
          </Typography>
          <Typography variant="h3" color="white" fontWeight={700}>
            Roe&apos;s POS
          </Typography>
          <Typography sx={{ color: 'rgba(255,255,255,0.8)' }}>
            Enter your PIN to get started
          </Typography>
        </Box>

        <Card sx={{ borderRadius: 3, mb: 3 }}>
          <CardContent>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
                PIN
              </Typography>
              <Stack direction="row" justifyContent="center" spacing={2}>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <Box
                    key={i}
                    sx={{
                      width: 14,
                      height: 14,
                      borderRadius: '50%',
                      border: '2px solid #1976D2',
                      bgcolor: i <= pin.length ? '#1976D2' : 'transparent',
                    }}
                  />
                ))}
              </Stack>
            </Box>

            {showError && error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, minmax(70px, 1fr))',
                gap: 1.5,
              }}
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((number) => (
                <Button
                  key={number}
                  variant="outlined"
                  onClick={() => handleNumberPress(number.toString())}
                  sx={{ py: 2, fontSize: 24, fontWeight: 700, borderRadius: 999 }}
                >
                  {number}
                </Button>
              ))}

              <Button onClick={() => setPin('')} color="warning" sx={{ py: 2, borderRadius: 999 }}>
                Clear
              </Button>
              <Button variant="outlined" onClick={() => handleNumberPress('0')} sx={{ py: 2, fontSize: 24, borderRadius: 999 }}>
                0
              </Button>
              <Button onClick={handleBackspace} color="error" sx={{ py: 2, borderRadius: 999 }}>
                ⌫
              </Button>
            </Box>
          </CardContent>
        </Card>

        <Button
          variant="contained"
          fullWidth
          onClick={handleLogin}
          disabled={isLoading || pin.length < 4}
          sx={{ py: 1.5, borderRadius: 2, mb: 2 }}
        >
          {isLoading ? <CircularProgress size={22} color="inherit" /> : 'Login'}
        </Button>

        <Typography textAlign="center" sx={{ color: 'rgba(255,255,255,0.7)' }}>
          Ask your manager if you don&apos;t know your PIN
        </Typography>
      </Box>
    </Box>
  );
};

export default LoginScreen;