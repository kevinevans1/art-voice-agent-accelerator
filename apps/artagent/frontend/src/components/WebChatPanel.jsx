/**
 * WebChatPanel - Omnichannel Web Chat Component
 * 
 * This component provides a web-based chat interface that connects to the
 * backend via WebSocket. It demonstrates omnichannel context preservation:
 * when a customer switches from voice to webchat, their conversation context
 * is automatically available.
 * 
 * Features:
 * - WebSocket connection to /api/v1/channels/webchat/ws/{customer_id}
 * - Displays handoff context when coming from voice call
 * - Real-time bidirectional messaging
 * - Shows customer context summary
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
  Divider,
} from '@mui/material';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import PhoneIcon from '@mui/icons-material/Phone';
import ChatIcon from '@mui/icons-material/Chat';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import HistoryIcon from '@mui/icons-material/History';
import { WS_URL, API_BASE_URL } from '../config/constants.js';
import logger from '../utils/logger.js';

// Styles
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#f8fafc',
    borderRadius: '16px',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  },
  header: {
    padding: '16px 20px',
    background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  contextBanner: {
    padding: '12px 20px',
    backgroundColor: '#ecfdf5',
    borderBottom: '1px solid #d1fae5',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  messageBubble: (isUser) => ({
    maxWidth: '75%',
    padding: '12px 16px',
    borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
    backgroundColor: isUser ? '#3b82f6' : 'white',
    color: isUser ? 'white' : '#1e293b',
    alignSelf: isUser ? 'flex-end' : 'flex-start',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    wordWrap: 'break-word',
  }),
  inputContainer: {
    padding: '16px 20px',
    backgroundColor: 'white',
    borderTop: '1px solid #e2e8f0',
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  statusDot: (connected) => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: connected ? '#22c55e' : '#ef4444',
    boxShadow: connected ? '0 0 8px #22c55e' : '0 0 8px #ef4444',
  }),
};

/**
 * Message component for chat bubbles
 */
const Message = ({ message, isUser }) => (
  <Box sx={styles.messageBubble(isUser)}>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
      {isUser ? (
        <PersonIcon sx={{ fontSize: 16, opacity: 0.8 }} />
      ) : (
        <SmartToyIcon sx={{ fontSize: 16, opacity: 0.8 }} />
      )}
      <Typography variant="caption" sx={{ opacity: 0.8 }}>
        {isUser ? 'You' : message.agent || 'Agent'}
      </Typography>
    </Box>
    <Typography variant="body2">{message.content}</Typography>
    {message.timestamp && (
      <Typography variant="caption" sx={{ opacity: 0.6, fontSize: '10px', display: 'block', mt: 0.5 }}>
        {new Date(message.timestamp).toLocaleTimeString()}
      </Typography>
    )}
  </Box>
);

/**
 * Context banner showing handoff information
 */
const ContextBanner = ({ context, sourceChannel }) => (
  <Box sx={styles.contextBanner}>
    <HistoryIcon sx={{ color: '#10b981', mt: 0.5 }} />
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <Typography variant="subtitle2" sx={{ color: '#065f46', fontWeight: 600 }}>
          Conversation Continued from {sourceChannel === 'voice' ? 'Phone Call' : sourceChannel}
        </Typography>
        <Chip 
          icon={<PhoneIcon sx={{ fontSize: 14 }} />} 
          label="Context Preserved" 
          size="small" 
          color="success" 
          variant="outlined"
          sx={{ height: 24 }}
        />
      </Box>
      <Typography variant="body2" sx={{ color: '#047857' }}>
        {context}
      </Typography>
    </Box>
  </Box>
);

/**
 * WebChatPanel Component
 * 
 * Props:
 * - customerId: Customer identifier (phone number or user ID)
 * - onClose: Callback when chat is closed
 */
export default function WebChatPanel({ customerId, onClose }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState(null);
  const [handoffContext, setHandoffContext] = useState(null);
  const [sourceChannel, setSourceChannel] = useState(null);
  
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // WebSocket connection
  useEffect(() => {
    if (!customerId) {
      setError('Customer ID is required');
      setConnecting(false);
      return;
    }

    const connectWebSocket = () => {
      setConnecting(true);
      setError(null);

      // Build WebSocket URL
      const wsBaseUrl = WS_URL || API_BASE_URL?.replace('http', 'ws') || '';
      const wsUrl = `${wsBaseUrl}/api/v1/channels/webchat/ws/${encodeURIComponent(customerId)}`;
      
      logger.info('[WebChat] Connecting to:', wsUrl);

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          logger.info('[WebChat] Connected');
          setConnected(true);
          setConnecting(false);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            logger.debug('[WebChat] Received:', data);

            switch (data.type) {
              case 'handoff':
                // Context from previous channel (e.g., voice call)
                setHandoffContext(data.context_summary || data.message);
                setSourceChannel(data.source_channel);
                setMessages((prev) => [...prev, {
                  type: 'system',
                  content: data.message || 'Welcome! I have your conversation history.',
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
                // Heartbeat response
                break;

              default:
                logger.warn('[WebChat] Unknown message type:', data.type);
            }
          } catch (e) {
            logger.error('[WebChat] Failed to parse message:', e);
          }
        };

        ws.onclose = (event) => {
          logger.info('[WebChat] Disconnected:', event.code, event.reason);
          setConnected(false);
          wsRef.current = null;

          // Attempt reconnect after 3 seconds if not intentional close
          if (event.code !== 1000) {
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
          }
        };

        ws.onerror = (error) => {
          logger.error('[WebChat] WebSocket error:', error);
          setError('Connection error. Retrying...');
          setConnecting(false);
        };

      } catch (e) {
        logger.error('[WebChat] Failed to connect:', e);
        setError('Failed to connect to chat server');
        setConnecting(false);
      }
    };

    connectWebSocket();

    // Cleanup
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
      }
    };
  }, [customerId]);

  // Send message handler
  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (!trimmed || !wsRef.current || !connected) return;

    // Add message to UI immediately
    setMessages((prev) => [...prev, {
      type: 'message',
      content: trimmed,
      timestamp: new Date().toISOString(),
      isUser: true,
    }]);

    // Send via WebSocket
    wsRef.current.send(JSON.stringify({
      type: 'message',
      content: trimmed,
    }));

    setInputValue('');
  }, [inputValue, connected]);

  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <Paper sx={styles.container} elevation={0}>
      {/* Header */}
      <Box sx={styles.header}>
        <ChatIcon />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: '1rem' }}>
            Utilities Support Chat
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>
            Customer: {customerId}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={styles.statusDot(connected)} />
          <Typography variant="caption">
            {connecting ? 'Connecting...' : connected ? 'Connected' : 'Disconnected'}
          </Typography>
        </Box>
      </Box>

      {/* Handoff Context Banner */}
      {handoffContext && (
        <ContextBanner context={handoffContext} sourceChannel={sourceChannel} />
      )}

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      )}

      {/* Loading */}
      {connecting && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress size={32} />
        </Box>
      )}

      {/* Messages */}
      <Box sx={styles.messagesContainer}>
        {messages.map((msg, idx) => (
          msg.type === 'system' ? (
            <Box key={idx} sx={{ textAlign: 'center', my: 1 }}>
              <Chip 
                label={msg.content} 
                size="small" 
                color={msg.isHandoff ? 'success' : 'default'}
                variant="outlined"
                icon={msg.isHandoff ? <HistoryIcon /> : undefined}
              />
            </Box>
          ) : (
            <Message key={idx} message={msg} isUser={msg.isUser} />
          )
        ))}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input */}
      <Box sx={styles.inputContainer}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Type your message..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!connected}
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: '24px',
              backgroundColor: '#f1f5f9',
            },
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!connected || !inputValue.trim()}
          sx={{
            backgroundColor: '#3b82f6',
            color: 'white',
            '&:hover': { backgroundColor: '#2563eb' },
            '&:disabled': { backgroundColor: '#e2e8f0', color: '#94a3b8' },
          }}
        >
          <SendRoundedIcon />
        </IconButton>
      </Box>
    </Paper>
  );
}
