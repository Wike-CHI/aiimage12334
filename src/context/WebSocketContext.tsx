/**
 * WebSocket Context
 * 提供全局共享的 WebSocket 连接，避免多个组件重复创建连接
 */

import React, { createContext, useContext, useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { WEBSOCKET_CONFIG } from '@/config';
import { useAuth } from '@/hooks/useAuth';

// 消息类型定义
export type WebSocketMessageType =
  | 'task_update'
  | 'task_complete'
  | 'task_failed'
  | 'pong';

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

export interface WebSocketMessage {
  type: WebSocketMessageType;
  task_id?: number;
  data: TaskProgressData;
}

// 回调类型
type TaskUpdateCallback = (data: TaskProgressData, taskId: number) => void;
type TaskCompleteCallback = (data: TaskProgressData, taskId: number) => void;
type TaskFailedCallback = (error: string, taskId: number) => void;

// Context 接口
interface WebSocketContextValue {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  subscribe: (taskId: number, callbacks: {
    onUpdate?: TaskUpdateCallback;
    onComplete?: TaskCompleteCallback;
    onFailed?: TaskFailedCallback;
  }) => () => void;
  unsubscribe: (taskId: number) => void;
  unsubscribeAll: () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export function useWebSocketContext() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}

// 订阅者记录
interface Subscriber {
  taskId: number;
  callbacks: {
    onUpdate?: TaskUpdateCallback;
    onComplete?: TaskCompleteCallback;
    onFailed?: TaskFailedCallback;
  };
}

// Provider 组件
export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const subscribersRef = useRef<Map<number, Subscriber[]>>(new Map());
  const isConnectingRef = useRef(false);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  // 发送消息给订阅者
  const notifySubscribers = useCallback((message: WebSocketMessage) => {
    if (!message.task_id) {
      console.log('[WebSocket] No task_id in message, skipping');
      return;
    }

    const taskId = message.task_id;
    console.log('[WebSocket] notifySubscribers called for task:', taskId, 'type:', message.type);
    console.log('[WebSocket] Current subscribers:', Array.from(subscribersRef.current.keys()));

    // 通知特定任务的订阅者
    const taskSubscribers = subscribersRef.current.get(taskId);
    console.log('[WebSocket] Task subscribers for', taskId, ':', taskSubscribers?.length || 0);
    if (taskSubscribers) {
      taskSubscribers.forEach((subscriber, index) => {
        console.log('[WebSocket] Calling subscriber', index, 'for task', taskId);
        switch (message.type) {
          case 'task_update':
            subscriber.callbacks.onUpdate?.(message.data, taskId);
            break;
          case 'task_complete':
            subscriber.callbacks.onComplete?.(message.data, taskId);
            break;
          case 'task_failed':
            subscriber.callbacks.onFailed?.(message.data.error_message || 'Unknown error', taskId);
            break;
        }
      });
    }

    // 通知全局订阅者 (taskId = 0 表示监听所有任务)
    const globalSubscribers = subscribersRef.current.get(0);
    console.log('[WebSocket] Global subscribers:', globalSubscribers?.length || 0);
    if (globalSubscribers) {
      globalSubscribers.forEach((subscriber, index) => {
        console.log('[WebSocket] Calling global subscriber', index);
        switch (message.type) {
          case 'task_update':
            subscriber.callbacks.onUpdate?.(message.data, taskId);
            break;
          case 'task_complete':
            subscriber.callbacks.onComplete?.(message.data, taskId);
            break;
          case 'task_failed':
            subscriber.callbacks.onFailed?.(message.data.error_message || 'Unknown error', taskId);
            break;
        }
      });
    }
  }, []);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (isConnectingRef.current) {
      console.log('[WebSocket] Already connecting, skipping');
      return;
    }

    if (!user) {
      console.log('[WebSocket] No user, skipping connect');
      return;
    }

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

    isConnectingRef.current = true;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        isConnectingRef.current = false;
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;

        // 启动心跳
        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, WEBSOCKET_CONFIG.heartbeat.interval);
      };

      ws.onmessage = (event) => {
        try {
          // 后端发送的 pong 是纯文本，需要先检查
          if (event.data === 'pong') {
            // 心跳响应，忽略
            return;
          }

          console.log('[WebSocket] Received raw message:', event.data);
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] Parsed message:', message);

          setLastMessage(message);

          // 只处理任务相关消息
          if (message.type === 'task_update' || message.type === 'task_complete' || message.type === 'task_failed') {
            console.log('[WebSocket] Notifying subscribers for task:', message.task_id, 'type:', message.type);
            notifySubscribers(message);
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        isConnectingRef.current = false;
        setIsConnected(false);

        // 清理心跳定时器
        if (heartbeatTimerRef.current) {
          clearInterval(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }

        // 尝试重连
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
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      isConnectingRef.current = false;
    }
  }, [user, notifySubscribers]);

  // 断开连接
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Manual disconnect');

    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    isConnectingRef.current = false;
    setIsConnected(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  // 订阅任务更新
  const subscribe = useCallback((taskId: number, callbacks: {
    onUpdate?: TaskUpdateCallback;
    onComplete?: TaskCompleteCallback;
    onFailed?: TaskFailedCallback;
  }) => {
    console.log('[WebSocket] Subscribe called for task:', taskId);
    if (!subscribersRef.current.has(taskId)) {
      subscribersRef.current.set(taskId, []);
      console.log('[WebSocket] Created new subscriber list for task:', taskId);
    }
    const subscribers = subscribersRef.current.get(taskId)!;
    subscribers.push({ taskId, callbacks });
    console.log('[WebSocket] Total subscribers for task', taskId, ':', subscribers.length);

    // 返回取消订阅函数
    return () => {
      console.log('[WebSocket] Unsubscribe called for task:', taskId);
      unsubscribe(taskId);
    };
  }, []);

  // 取消订阅
  const unsubscribe = useCallback((taskId: number) => {
    // 直接删除该任务的所有订阅者，而非只移除一个
    subscribersRef.current.delete(taskId);
  }, []);

  // 取消所有订阅
  const unsubscribeAll = useCallback(() => {
    subscribersRef.current.clear();
  }, []);

  // 自动连接/断开
  useEffect(() => {
    if (user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, connect, disconnect]);

  const value = useMemo(() => ({
    isConnected,
    lastMessage,
    subscribe,
    unsubscribe,
    unsubscribeAll,
  }), [isConnected, lastMessage, subscribe, unsubscribe, unsubscribeAll]);

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

// 便捷 Hook：订阅单个任务
export function useTaskSubscription(
  taskId: number | null,
  callbacks: {
    onUpdate?: (data: TaskProgressData) => void;
    onComplete: (data: TaskProgressData) => void;
    onError?: (error: string) => void;
  }
) {
  const { isConnected, subscribe, unsubscribeAll } = useWebSocketContext();
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    const wrappedCallbacks = {
      onUpdate: callbacks.onUpdate ? (data: TaskProgressData) => callbacks.onUpdate?.(data) : undefined,
      onComplete: (data: TaskProgressData) => callbacks.onComplete(data),
      onFailed: (error: string) => callbacks.onError?.(error),
    };

    cleanupRef.current = subscribe(taskId, wrappedCallbacks);

    return () => {
      cleanupRef.current?.();
    };
  }, [taskId, callbacks, subscribe]);

  return { isConnected };
}
