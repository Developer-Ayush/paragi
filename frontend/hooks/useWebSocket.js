import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Custom hook to manage WebSocket connection for real-time chat synchronization.
 * @param {string} userId - The user ID to subscribe to.
 * @param {string} baseUrl - The base URL for the WebSocket (e.g., ws://localhost:8000).
 * @returns {Object} - { messages, sendMessage, isConnected }
 */
export const useWebSocket = (userId, baseUrl) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!userId || !baseUrl) return;

    // Construct WebSocket URL
    // Handle https -> wss and http -> ws
    const wsBase = baseUrl.replace(/^http/, 'ws');
    const url = `${wsBase}/ws/${userId}`;

    console.log(`[WebSocket] Connecting to ${url}...`);
    const socket = new WebSocket(url);

    socket.onopen = () => {
      console.log('[WebSocket] Connected');
      setIsConnected(true);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] Message received:', data);
        setLastMessage(data);
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err);
      }
    };

    socket.onclose = (event) => {
      console.log(`[WebSocket] Disconnected (code: ${event.code})`);
      setIsConnected(false);
      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    socket.onerror = (err) => {
      console.error('[WebSocket] Error:', err);
      socket.close();
    };

    socketRef.current = socket;
  }, [userId, baseUrl]);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === 'string' ? msg : JSON.stringify(msg));
      return true;
    }
    console.warn('[WebSocket] Cannot send message: Not connected');
    return false;
  }, []);

  return { lastMessage, sendMessage, isConnected };
};
