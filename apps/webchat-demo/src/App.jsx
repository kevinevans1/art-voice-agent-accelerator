/**
 * Omnichannel WebChat Demo App
 * 
 * This standalone application demonstrates the omnichannel context preservation
 * feature. When a customer has previously called via voice, their conversation
 * context is automatically available in the webchat.
 * 
 * Demo Flow:
 * 1. Customer calls via voice (main artagent app) - talks about a power outage
 * 2. Voice agent saves context to CustomerContextManager
 * 3. Customer opens this webchat app with the same phone number
 * 4. WebChat automatically shows: "I see you recently called about a power outage..."
 * 5. Customer doesn't need to repeat themselves!
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Button,
  Card,
  CardContent,
  Fade,
  Grow,
} from '@mui/material';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import PhoneIcon from '@mui/icons-material/Phone';
import ChatIcon from '@mui/icons-material/Chat';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import HistoryIcon from '@mui/icons-material/History';
import ElectricBoltIcon from '@mui/icons-material/ElectricBolt';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WifiOffIcon from '@mui/icons-material/WifiOff';

// Theme
const theme = createTheme({
  palette: {
    primary: {
      main: '#3b82f6',
    },
    secondary: {
      main: '#8b5cf6',
    },
    success: {
      main: '#10b981',
    },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  shape: {
    borderRadius: 12,
  },
});

// Get backend URL from environment or use default
const getBackendUrl = () => {
  // Check for Vite env variable
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  // Check for runtime config (injected by entrypoint)
  if (window.__RUNTIME_CONFIG__?.BACKEND_URL) {
    return window.__RUNTIME_CONFIG__.BACKEND_URL;
  }
  // Check URL params (for quick testing)
  const params = new URLSearchParams(window.location.search);
  if (params.get('backend')) {
    return params.get('backend');
  }
  // Default to localhost for development
  return 'http://localhost:8000';
};

/**
 * Message component
 */
const Message = ({ message, isUser }) => (
  <Grow in={true}>
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Box
        sx={{
          maxWidth: '80%',
          p: 2,
          borderRadius: isUser ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
          bgcolor: isUser ? 'primary.main' : 'white',
          color: isUser ? 'white' : 'text.primary',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          {isUser ? (
            <PersonIcon sx={{ fontSize: 16, opacity: 0.8 }} />
          ) : (
            <SmartToyIcon sx={{ fontSize: 16, color: 'primary.main' }} />
          )}
          <Typography variant="caption" sx={{ opacity: 0.8, fontWeight: 500 }}>
            {isUser ? 'You' : message.agent || 'Utilities Agent'}
          </Typography>
        </Box>
        <Typography variant="body1">{message.content}</Typography>
      </Box>
      {message.timestamp && (
        <Typography variant="caption" sx={{ opacity: 0.5, mt: 0.5, px: 1 }}>
          {new Date(message.timestamp).toLocaleTimeString()}
        </Typography>
      )}
    </Box>
  </Grow>
);

/**
 * Handoff Banner - Shows when context from voice call is available
 */
const HandoffBanner = ({ context, sourceChannel, collectedData }) => (
  <Fade in={true}>
    <Card 
      sx={{ 
        mb: 3, 
        bgcolor: '#ecfdf5', 
        border: '1px solid #d1fae5',
        boxShadow: '0 4px 20px rgba(16, 185, 129, 0.15)',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Box
            sx={{
              p: 1.5,
              borderRadius: '50%',
              bgcolor: '#d1fae5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <CheckCircleIcon sx={{ color: '#10b981', fontSize: 28 }} />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="h6" sx={{ color: '#065f46', fontWeight: 600 }}>
                Conversation Continued
              </Typography>
              <Chip
                icon={<PhoneIcon sx={{ fontSize: 14 }} />}
                label={`From ${sourceChannel === 'voice' ? 'Phone Call' : sourceChannel}`}
                size="small"
                color="success"
                variant="outlined"
              />
            </Box>
            <Typography variant="body2" sx={{ color: '#047857', mb: 2 }}>
              {context}
            </Typography>
            
            {/* Show collected data if available */}
            {collectedData && Object.keys(collectedData).length > 0 && (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {Object.entries(collectedData).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={`${key.replace(/_/g, ' ')}: ${value}`}
                    size="small"
                    sx={{ 
                      bgcolor: '#d1fae5', 
                      color: '#065f46',
                      textTransform: 'capitalize',
                    }}
                  />
                ))}
              </Box>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  </Fade>
);

/**
 * Customer ID Input Screen
 */
const CustomerIdInput = ({ onSubmit, loading }) => {
  const [customerId, setCustomerId] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (customerId.trim()) {
      onSubmit(customerId.trim());
    }
  };

  return (
    <Paper
      sx={{
        p: 4,
        maxWidth: 400,
        width: '100%',
        textAlign: 'center',
        borderRadius: 4,
        boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}
    >
      <Box
        sx={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          bgcolor: 'primary.main',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mx: 'auto',
          mb: 3,
        }}
      >
        <ElectricBoltIcon sx={{ fontSize: 40, color: 'white' }} />
      </Box>
      
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
        PowerGas Utilities
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        WebChat Support - Omnichannel Demo
      </Typography>
      
      <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
        <Typography variant="body2">
          <strong>Demo:</strong> Enter the same phone number you used for the voice call 
          to see your conversation context automatically loaded.
        </Typography>
      </Alert>
      
      <form onSubmit={handleSubmit}>
        <TextField
          fullWidth
          label="Phone Number or Customer ID"
          placeholder="+1234567890"
          value={customerId}
          onChange={(e) => setCustomerId(e.target.value)}
          disabled={loading}
          sx={{ mb: 2 }}
          helperText="Use your phone number from the voice call"
        />
        <Button
          type="submit"
          variant="contained"
          fullWidth
          size="large"
          disabled={!customerId.trim() || loading}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ChatIcon />}
          sx={{
            py: 1.5,
            borderRadius: 3,
            textTransform: 'none',
            fontWeight: 600,
          }}
        >
          {loading ? 'Connecting...' : 'Start Chat'}
        </Button>
      </form>
    </Paper>
  );
};

/**
 * Main Chat Interface
 */
const ChatInterface = ({ customerId, backendUrl, onDisconnect }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState(null);
  const [handoffContext, setHandoffContext] = useState(null);
  const [sourceChannel, setSourceChannel] = useState(null);
  const [collectedData, setCollectedData] = useState(null);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Auto-scroll
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      setConnecting(true);
      setError(null);

      const wsUrl = backendUrl.replace(/^http/, 'ws');
      const fullUrl = `${wsUrl}/api/v1/channels/webchat/ws/${encodeURIComponent(customerId)}`;
      
      console.log('[WebChat] Connecting to:', fullUrl);

      try {
        const ws = new WebSocket(fullUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WebChat] Connected');
          setConnected(true);
          setConnecting(false);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('[WebChat] Received:', data);

            switch (data.type) {
              case 'handoff':
                // Context from previous channel!
                setHandoffContext(data.context_summary || data.message);
                setSourceChannel(data.source_channel);
                if (data.collected_data) {
                  setCollectedData(data.collected_data);
                }
                setMessages((prev) => [...prev, {
                  type: 'system',
                  content: "I have your conversation history from your phone call. No need to repeat yourself!",
                  timestamp: data.timestamp,
                  isHandoff: true,
                }]);
                break;

              case 'system':
                setMessages((prev) => [...prev, {
                  type: 'system',
                  content: data.content,
                  timestamp: data.timestamp,
                }]);
                break;

              case 'message':
                setMessages((prev) => [...prev, {
                  type: 'message',
                  content: data.content,
                  agent: data.agent,
                  timestamp: data.timestamp,
                  isUser: false,
                }]);
                break;

              case 'error':
                setError(data.content);
                break;

              case 'pong':
                break;

              default:
                console.warn('[WebChat] Unknown message type:', data.type);
            }
          } catch (e) {
            console.error('[WebChat] Parse error:', e);
          }
        };

        ws.onclose = (event) => {
          console.log('[WebChat] Disconnected:', event.code);
          setConnected(false);
          wsRef.current = null;

          if (event.code !== 1000) {
            setError('Connection lost. Reconnecting...');
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
          }
        };

        ws.onerror = () => {
          setError('Connection error');
          setConnecting(false);
        };

      } catch (e) {
        console.error('[WebChat] Connection failed:', e);
        setError('Failed to connect');
        setConnecting(false);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000);
      }
    };
  }, [customerId, backendUrl]);

  // Send message
  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || !wsRef.current || !connected) return;

    setMessages((prev) => [...prev, {
      type: 'message',
      content: trimmed,
      timestamp: new Date().toISOString(),
      isUser: true,
    }]);

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content: trimmed,
    }));

    setInputValue('');
  }, [inputValue, connected]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <Paper
      sx={{
        width: '100%',
        maxWidth: 500,
        height: '80vh',
        maxHeight: 700,
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 4,
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: 2,
        }}
      >
        <Box
          sx={{
            p: 1,
            borderRadius: '50%',
            bgcolor: 'rgba(255,255,255,0.2)',
          }}
        >
          <ElectricBoltIcon />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            PowerGas Utilities
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>
            Customer: {customerId}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              bgcolor: connected ? '#22c55e' : connecting ? '#fbbf24' : '#ef4444',
              boxShadow: connected ? '0 0 8px #22c55e' : undefined,
            }}
          />
          <Typography variant="caption">
            {connecting ? 'Connecting...' : connected ? 'Online' : 'Offline'}
          </Typography>
        </Box>
      </Box>

      {/* Messages Area */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 2,
          bgcolor: '#f8fafc',
        }}
      >
        {/* Handoff Banner */}
        {handoffContext && (
          <HandoffBanner
            context={handoffContext}
            sourceChannel={sourceChannel}
            collectedData={collectedData}
          />
        )}

        {/* Error */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Connecting */}
        {connecting && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Messages */}
        {messages.map((msg, idx) =>
          msg.type === 'system' ? (
            <Box key={idx} sx={{ textAlign: 'center', my: 2 }}>
              <Chip
                label={msg.content}
                color={msg.isHandoff ? 'success' : 'default'}
                variant={msg.isHandoff ? 'filled' : 'outlined'}
                icon={msg.isHandoff ? <HistoryIcon /> : undefined}
              />
            </Box>
          ) : (
            <Message key={idx} message={msg} isUser={msg.isUser} />
          )
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box
        sx={{
          p: 2,
          bgcolor: 'white',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          gap: 1.5,
        }}
      >
        <TextField
          fullWidth
          placeholder="Type your message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!connected}
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 6,
              bgcolor: '#f1f5f9',
            },
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!connected || !inputValue.trim()}
          sx={{
            bgcolor: 'primary.main',
            color: 'white',
            '&:hover': { bgcolor: 'primary.dark' },
            '&:disabled': { bgcolor: '#e2e8f0' },
          }}
        >
          <SendRoundedIcon />
        </IconButton>
      </Box>
    </Paper>
  );
};

/**
 * Main App
 */
export default function App() {
  const [customerId, setCustomerId] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const backendUrl = getBackendUrl();

  // Check URL params for customer_id (for direct handoff links)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('customer_id') || params.get('phone');
    if (id) {
      setCustomerId(id);
    }
  }, []);

  const handleConnect = (id) => {
    setConnecting(true);
    // Brief delay for visual feedback
    setTimeout(() => {
      setCustomerId(id);
      setConnecting(false);
    }, 500);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {customerId ? (
        <ChatInterface
          customerId={customerId}
          backendUrl={backendUrl}
          onDisconnect={() => setCustomerId(null)}
        />
      ) : (
        <CustomerIdInput onSubmit={handleConnect} loading={connecting} />
      )}
    </ThemeProvider>
  );
}
