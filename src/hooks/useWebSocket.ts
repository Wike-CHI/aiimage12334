/**
 * WebSocket Hook
 * 提供 WebSocket 连接管理、自动重连、心跳保活和消息分发功能
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { WEBSOCKET_CONFIG } from '@/config';
import { useAuth } from './useAuth';

// 消息类型定义
export type WebSocketMessageType =
  | 'task_update'      // 任务进度更新
  | 'task_complete'    // 任务完成
  | 'task_failed'      // 任务失败
  | 'pong';            // 心跳响应

// 任务进度数据
export interface TaskProgressData {
  task_id: number;
  status: string;
  progress?: number;
  result_image_url?: string;
  elapsed_time?: number;
  estimated_remaining_seconds?: number;
  error_message?: string;
  updated_at?: string;
}

// WebSocket 消息
export interface WebSocketMessage {
  type: WebSocketMessageType;
  task_id?: number;
  data: TaskProgressData;
}

// Hook 选项
interface UseWebSocketOptions {
  onTaskUpdate?: (data: TaskProgressData, taskId: number) => void;
  onTaskComplete?: (data: TaskProgressData, taskId: number) => void;
  onTaskFailed?: (error: string, taskId: number) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  enabled?: boolean;
}

// Hook 返回接口
interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  connect: () => void;
  disconnect: () => void;
  send: (data: object) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { user } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const connect = useCallback(() => {
    if (!user) {
      console.log('[WebSocket] No user, skipping connect');
      return;
    }

    // 如果已有连接且状态正常，不重复连接
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      console.log('[WebSocket] No token available');
      return;
    }

    const wsUrl = `${WEBSOCKET_CONFIG.url}?token=${token}`;
    console.log('[WebSocket] Connecting to:', wsUrl.replace(token, '***'));

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        options.onConnect?.();

        // 启动心跳
        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, WEBSOCKET_CONFIG.heartbeat.interval);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);

          switch (message.type) {
            case 'task_update':
              message.task_id && options.onTaskUpdate?.(message.data, message.task_id);
              break;
            case 'task_complete':
              message.task_id && options.onTaskComplete?.(message.data, message.task_id);
              break;
            case 'task_failed':
              message.task_id && options.onTaskFailed?.(message.data.error_message || 'Unknown error', message.task_id);
              break;
            case 'pong':
              // 心跳响应，忽略
              break;
            default:
              console.log('[WebSocket] Unknown message type:', message.type);
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        options.onDisconnect?.();

        // 清理心跳定时器
        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }

        // 尝试重连 (如果不是因为认证失败 code=4001)
        if (event.code !== 4001 && reconnectAttemptsRef.current < WEBSOCKET_CONFIG.reconnect.maxAttempts) {
          const delay = Math.min(
            WEBSOCKET_CONFIG.reconnect.delay *
            Math.pow(WEBSOCKET_CONFIG.reconnect.backoff, reconnectAttemptsRef.current),
            WEBSOCKET_CONFIG.reconnect.maxDelay
          );
          reconnectAttemptsRef.current++;
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
          setTimeout(connect, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        options.onError?.(error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
    }
  }, [user, options]);

  const disconnect = useCallback(() => {
    console.log('[WebSocket] Manual disconnect');

    // 清理心跳定时器
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }

    // 关闭连接
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    setIsConnected(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // 自动连接/断开
  useEffect(() => {
    if (options.enabled !== false && user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, options.enabled, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
    send,
  };
}

/**
 * 任务状态监听 Hook
 * 专门用于监听单个任务的状态变化
 */
export function useTaskListener(
  taskId: number | null,
  callbacks: {
    onUpdate?: (data: TaskProgressData) => void;
    onComplete: (data: TaskProgressData) => void;
    onError?: (error: string) => void;
  }
) {
  const { isConnected, ...ws } = useWebSocket({
    onTaskUpdate: (data, id) => {
      if (id === taskId) {
        callbacks.onUpdate?.(data);
      }
    },
    onTaskComplete: (data, id) => {
      if (id === taskId) {
        callbacks.onComplete(data);
      }
    },
    onTaskFailed: (error, id) => {
      if (id === taskId) {
        callbacks.onError?.(error);
      }
    },
    enabled: !!taskId,
  });

  return { isConnected, ...ws };
}
