import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { generationV2API } from "@/integrations/api/client";
import { useAuth } from "./useAuth";
import { useWebSocketContext, TaskProgressData } from "@/context/WebSocketContext";

interface Task {
  id: number;
  user_id: number;
  original_image_url: string | null;
  result_image_url: string | null;
  status: string;
  credits_used: number;
  width: number;
  height: number;
  created_at: string;
}

export function useTaskHistory(autoRefresh: boolean = false) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const tasksRef = useRef<Task[]>([]);

  const fetchTasks = useCallback(async () => {
    if (!user) {
      setTasks([]);
      return;
    }

    setIsLoading(true);
    try {
      // 使用V2 API直接从数据库查询，实时反映任务状态
      const response = await generationV2API.getTasks(0, 50);
      const newTasks = response.data.tasks || [];
      tasksRef.current = newTasks;
      setTasks(newTasks);
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  // WebSocket 消息处理器 - 保持稳定引用
  const handleTaskUpdate = useCallback((data: TaskProgressData) => {
    // 更新本地任务列表中的对应任务状态
    setTasks(prev => prev.map(task =>
      task.id === data.task_id
        ? { ...task, status: data.status }
        : task
    ));
    // 同时更新 ref
    tasksRef.current = tasksRef.current.map(task =>
      task.id === data.task_id
        ? { ...task, status: data.status }
        : task
    );
  }, []);

  const handleTaskComplete = useCallback((data: TaskProgressData) => {
    // 更新本地任务列表中的对应任务
    setTasks(prev => prev.map(task =>
      task.id === data.task_id
        ? {
            ...task,
            status: 'completed',
            result_image_url: data.result_image_url || task.result_image_url,
          }
        : task
    ));
    // 同时更新 ref
    tasksRef.current = tasksRef.current.map(task =>
      task.id === data.task_id
        ? {
            ...task,
            status: 'completed',
            result_image_url: data.result_image_url || task.result_image_url,
          }
        : task
    );
  }, []);

  const handleTaskFailed = useCallback((data: TaskProgressData) => {
    // 更新本地任务列表中的对应任务状态为失败
    setTasks(prev => prev.map(task =>
      task.id === data.task_id
        ? { ...task, status: 'failed' }
        : task
    ));
    // 同时更新 ref
    tasksRef.current = tasksRef.current.map(task =>
      task.id === data.task_id
        ? { ...task, status: 'failed' }
        : task
    );
  }, []);

  // 使用全局 WebSocket Context 订阅任务更新
  const { isConnected, subscribe, unsubscribeAll } = useWebSocketContext();

  // 订阅所有任务更新
  useEffect(() => {
    if (!isConnected) return;

    const unsubscribeTaskUpdate = subscribe(0, { // 0 表示监听所有任务
      onUpdate: (data, taskId) => handleTaskUpdate({ ...data, task_id: taskId }),
    });

    const unsubscribeTaskComplete = subscribe(0, {
      onComplete: (data, taskId) => handleTaskComplete({ ...data, task_id: taskId }),
    });

    const unsubscribeTaskFailed = subscribe(0, {
      onFailed: (error, taskId) => handleTaskFailed({ task_id: taskId, status: 'failed', error_message: error } as TaskProgressData),
    });

    return () => {
      unsubscribeTaskUpdate();
      unsubscribeTaskComplete();
      unsubscribeTaskFailed();
    };
  }, [isConnected, subscribe, handleTaskUpdate, handleTaskComplete, handleTaskFailed]);

  // 手动刷新函数
  const refetch = useCallback(async () => {
    await fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!user) {
      setTasks([]);
      tasksRef.current = [];
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // 初始获取一次
    fetchTasks();

    // 如果 WebSocket 未连接或 autoRefresh 为 true，使用轮询作为补充
    if (autoRefresh || !isConnected) {
      intervalRef.current = setInterval(() => {
        fetchTasks();
      }, 5000); // 5秒间隔，比之前更长，因为有 WebSocket 作为主要通知
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [user, fetchTasks, autoRefresh, isConnected]);

  return { tasks, isLoading, refetch, isConnected };
}
