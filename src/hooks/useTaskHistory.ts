import { useState, useEffect, useCallback, useRef } from "react";
import { generationAPI } from "@/integrations/api/client";
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

export function useTaskHistory() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchTasks = useCallback(async () => {
    if (!user) {
      setTasks([]);
      return;
    }

    try {
      const response = await generationAPI.getTasks(0, 50);
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error("Error fetching tasks:", error);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user) {
      setTasks([]);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Initial fetch
    setIsLoading(true);
    fetchTasks();

    // Poll every 2 seconds to get updated status
    intervalRef.current = setInterval(() => {
      fetchTasks();
    }, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [user, fetchTasks]);

  return { tasks, isLoading, refetch: fetchTasks };
}
