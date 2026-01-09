import { useState, useCallback, useEffect, useRef } from 'react';
import { generationV2API } from '@/integrations/api/client';
import { useAuth } from './useAuth';
import { useToast } from './use-toast';
import { useWebSocketContext, TaskProgressData } from '@/context/WebSocketContext';

interface ProcessResult {
  success: boolean;
  task_id: number | null;
  result_image: string | null;
  elapsed_time: number | null;
  error_message?: string;
}

interface TaskStatus {
  task_id: number;
  status: string;
  result_image_url: string | null;
  elapsed_time: number | null;
  estimated_remaining_seconds: number | null;
  error_message: string | null;
}

interface UseImageGenerationV2Options {
  customPrompt?: string;
  timeoutSeconds?: number;
  aspectRatio?: string;
  imageSize?: string;
}

interface UseImageGenerationV2Return {
  processImage: (file: File, aspectRatio?: string, imageSize?: string) => Promise<ProcessResult>;
  processImageAsync: (file: File, aspectRatio?: string, imageSize?: string) => Promise<number>;
  pollTaskStatus: (taskId: number, onComplete: (result: ProcessResult) => void, onError?: (error: string) => void) => void;
  listenTaskStatus: (taskId: number, callbacks: {
    onUpdate?: (data: TaskProgressData) => void;
    onComplete: (data: TaskProgressData) => Promise<void>;
    onError?: (error: string) => void;
  }) => () => void;
  isProcessing: boolean;
  elapsedTime: number | null;
  estimatedRemainingTime: number | null;
  error: string | null;
}

export function useImageGenerationV2(
  options: UseImageGenerationV2Options = {}
): UseImageGenerationV2Return {
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedTime, setElapsedTime] = useState<number | null>(null);
  const [estimatedRemainingTime, setEstimatedRemainingTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePollingTasks, setActivePollingTasks] = useState<Set<number>>(new Set());

  const { user, refreshProfile } = useAuth();
  const { toast } = useToast();
  const wsContext = useWebSocketContext();

  // 清理轮询任务
  useEffect(() => {
    return () => {
      activePollingTasks.forEach(taskId => {
        // 清理逻辑由组件自己管理
      });
    };
  }, [activePollingTasks]);

  // 同步处理（保持原有逻辑）
  const processImage = useCallback(async (file: File, aspectRatio?: string, imageSize?: string): Promise<ProcessResult> => {
    if (!user) {
      const errorMsg = '请先登录';
      setError(errorMsg);
      return { success: false, task_id: null, result_image: null, elapsed_time: null, error_message: errorMsg };
    }

    if (user.credits < 1) {
      const errorMsg = '积分不足';
      setError(errorMsg);
      return { success: false, task_id: null, result_image: null, elapsed_time: null, error_message: errorMsg };
    }

    setIsProcessing(true);
    setError(null);
    setElapsedTime(null);

    const startTime = Date.now();

    try {
      const result = await generationV2API.process(file, {
        customPrompt: options.customPrompt,
        timeoutSeconds: options.timeoutSeconds || 180,
        aspectRatio: aspectRatio || options.aspectRatio || '1:1',
        imageSize: imageSize || options.imageSize || '1K',
      });

      const elapsed = (Date.now() - startTime) / 1000;
      setElapsedTime(elapsed);

      const data = result.data;

      if (data.success) {
        await refreshProfile();

        toast({
          title: '生成成功',
          description: `白底图已生成，耗时 ${elapsed.toFixed(1)} 秒`,
        });

        return {
          success: true,
          task_id: data.task_id,
          result_image: data.result_image,
          elapsed_time: data.elapsed_time,
        };
      } else {
        const errorMsg = data.error_message || '处理失败';
        setError(errorMsg);

        toast({
          title: '生成失败',
          description: errorMsg,
          variant: 'destructive',
        });

        return {
          success: false,
          task_id: null,
          result_image: null,
          elapsed_time: elapsed,
          error_message: errorMsg,
        };
      }
    } catch (err) {
      const elapsed = (Date.now() - startTime) / 1000;
      setElapsedTime(elapsed);

      const errorMsg = err instanceof Error ? err.message : '处理失败，请稍后重试';
      setError(errorMsg);

      toast({
        title: '生成失败',
        description: errorMsg,
        variant: 'destructive',
      });

      return {
        success: false,
        task_id: null,
        result_image: null,
        elapsed_time: elapsed,
        error_message: errorMsg,
      };
    } finally {
      setIsProcessing(false);
    }
  }, [user, refreshProfile, options.customPrompt, options.timeoutSeconds, toast]);

  // 异步提交任务
  const processImageAsync = useCallback(async (file: File, aspectRatio?: string, imageSize?: string): Promise<number> => {
    console.log('[useImageGenerationV2] processImageAsync 开始');
    if (!user) {
      throw new Error('请先登录');
    }

    if (user.credits < 1) {
      throw new Error('积分不足');
    }

    const result = await generationV2API.submitAsync(file, {
      customPrompt: options.customPrompt,
      timeoutSeconds: options.timeoutSeconds || 180,
      aspectRatio: aspectRatio || options.aspectRatio || '1:1',
      imageSize: imageSize || options.imageSize || '1K',
    });

    if (result.data.task_id) {
      console.log('[useImageGenerationV2] 任务创建成功，task_id:', result.data.task_id);
      await refreshProfile();
      return Number(result.data.task_id);
    }

    throw new Error('创建任务失败');
  }, [user, refreshProfile, options.customPrompt, options.timeoutSeconds]);

  // 轮询任务状态
  const pollTaskStatus = useCallback((taskId: number, onComplete: (result: ProcessResult) => void, onError?: (error: string) => void) => {
    // 确保 taskId 是有效的数字
    const numericTaskId = Number(taskId);
    if (isNaN(numericTaskId) || !isFinite(numericTaskId)) {
      console.error('Invalid taskId:', taskId);
      onError?.('无效的任务ID');
      return;
    }

    console.log('Starting to poll task status:', numericTaskId);
    setActivePollingTasks(prev => new Set(prev).add(numericTaskId));

    const poll = async () => {
      let attempts = 0;
      const maxAttempts = 300; // 最多轮询 5 分钟 (300 * 1s)

      const check = async () => {
        try {
          const response = await generationV2API.getTaskStatus(numericTaskId);
          const status: TaskStatus = response.data;

          // 更新预估剩余时间
          if (status.status === 'PENDING' || status.status === 'PROCESSING') {
            setEstimatedRemainingTime(status.estimated_remaining_seconds);
          } else {
            setEstimatedRemainingTime(null);
          }

          if (status.status === 'COMPLETED') {
            // 任务完成
            await refreshProfile();
            toast({
              title: '生成成功',
              description: `白底图已生成，耗时 ${status.elapsed_time?.toFixed(1) || 0} 秒`,
            });

            onComplete({
              success: true,
              task_id: numericTaskId,
              result_image: status.result_image_url || null, // 从轮询结果获取图片URL
              elapsed_time: status.elapsed_time,
            });

            setActivePollingTasks(prev => {
              const next = new Set(prev);
              next.delete(numericTaskId);
              return next;
            });
            setEstimatedRemainingTime(null);
            return true;
          } else if (status.status === 'FAILED') {
            // 任务失败
            const errorMsg = status.error_message || '处理失败';
            setError(errorMsg);

            toast({
              title: '生成失败',
              description: errorMsg,
              variant: 'destructive',
            });

            onError?.(errorMsg);

            setActivePollingTasks(prev => {
              const next = new Set(prev);
              next.delete(numericTaskId);
              return next;
            });
            setEstimatedRemainingTime(null);
            return true;
          } else {
            // 仍在处理中，继续轮询
            attempts++;
            if (attempts >= maxAttempts) {
              onError?.('轮询超时，请稍后查看历史记录');
              setActivePollingTasks(prev => {
                const next = new Set(prev);
                next.delete(numericTaskId);
                return next;
              });
              return true;
            }
            return false;
          }
        } catch (err) {
          console.error('轮询任务状态失败:', err);
          attempts++;
          if (attempts >= maxAttempts) {
            onError?.('获取状态失败');
            setActivePollingTasks(prev => {
              const next = new Set(prev);
              next.delete(numericTaskId);
              return next;
            });
            return true;
          }
          return false;
        }
      };

      // 轮询间隔 1 秒
      while (true) {
        const done = await check();
        if (done) break;
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    };

    poll();
  }, [refreshProfile, toast]);

  // 使用全局 WebSocket Context 监听任务状态
  const activeCleanupRef = useRef<Map<number, (() => void) | null>>(new Map());

  const listenTaskStatus = useCallback((taskId: number, callbacks: {
    onUpdate?: (data: TaskProgressData) => void;
    onComplete: (data: TaskProgressData) => void;
    onError?: (error: string) => void;
  }) => {
    console.log('[listenTaskStatus] 开始监听任务:', taskId);
    const numericTaskId = Number(taskId);
    if (isNaN(numericTaskId) || !isFinite(numericTaskId)) {
      console.error('[listenTaskStatus] 无效的任务ID:', taskId);
      callbacks.onError?.('无效的任务ID');
      return () => {};
    }

    // 使用在 hook 顶层获取的 wsContext
    const { subscribe } = wsContext;

    const wrappedCallbacks = {
      onUpdate: (data: TaskProgressData) => {
        console.log('[listenTaskStatus] 任务更新:', { taskId: numericTaskId, status: data.status, progress: data.progress });
        // 更新预估剩余时间
        if (data.status === 'PROCESSING' || data.status === 'PENDING') {
          setEstimatedRemainingTime(data.estimated_remaining_seconds || null);
          setElapsedTime(data.elapsed_time || null);
        }
        callbacks.onUpdate?.(data);
      },
      onComplete: async (data: TaskProgressData) => {
        console.log('[listenTaskStatus] 任务完成:', { taskId: numericTaskId, data });
        setEstimatedRemainingTime(null);
        await refreshProfile();

        toast({
          title: '生成成功',
          description: `白底图已生成，耗时 ${data.elapsed_time?.toFixed(1) || 0} 秒`,
        });

        callbacks.onComplete(data);
      },
      onFailed: (error: string) => {
        console.log('[listenTaskStatus] 任务失败:', { taskId: numericTaskId, error });
        setEstimatedRemainingTime(null);
        setError(error);

        toast({
          title: '生成失败',
          description: error,
          variant: 'destructive',
        });

        callbacks.onError?.(error);
      },
    };

    const cleanup = subscribe(numericTaskId, wrappedCallbacks);

    // 保存清理函数
    activeCleanupRef.current.set(numericTaskId, cleanup);

    // 返回取消监听函数
    return () => {
      cleanup();
      activeCleanupRef.current.delete(numericTaskId);
    };
  }, [refreshProfile, toast]);

  // 清理所有监听器
  useEffect(() => {
    return () => {
      activeCleanupRef.current.forEach(cleanup => cleanup?.());
      activeCleanupRef.current.clear();
    };
  }, []);

  return {
    processImage,
    processImageAsync,
    pollTaskStatus,
    listenTaskStatus,
    isProcessing,
    elapsedTime,
    estimatedRemainingTime,
    error,
  };
}
