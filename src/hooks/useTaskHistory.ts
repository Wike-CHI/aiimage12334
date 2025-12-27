import { useState, useEffect, useCallback, useRef } from "react";
import { generationV2API } from "@/integrations/api/client";
import { useAuth } from "./useAuth";

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

  const fetchTasks = useCallback(async () => {
    if (!user) {
      setTasks([]);
      return;
    }

    setIsLoading(true);
    try {
      // 使用V2 API直接从数据库查询，实时反映任务状态
      const response = await generationV2API.getTasks(0, 50);
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  // 手动刷新函数
  const refetch = useCallback(async () => {
    await fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    if (!user) {
      setTasks([]);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // 初始获取一次
    fetchTasks();

    // V2任务同步完成，但为了一致性仍支持轮询刷新
    if (autoRefresh) {
      intervalRef.current = setInterval(() => {
        fetchTasks();
      }, 2000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [user, fetchTasks, autoRefresh]);

  return { tasks, isLoading, refetch };
}
