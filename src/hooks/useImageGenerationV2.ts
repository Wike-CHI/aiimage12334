import { useState, useCallback } from 'react';
import { generationV2API } from '@/integrations/api/client';
import { useAuth } from './useAuth';
import { useToast } from './use-toast';

interface ProcessResult {
  success: boolean;
  task_id: number | null;  // 数据库任务ID
  result_image: string | null;  // Base64 编码的图片数据
  elapsed_time: number | null;
  used_templates: string[] | null;
  error_message?: string;
}

interface TemplateInfo {
  template_id: string;
  name: string;
  category: string;
  description: string;
  priority: number;
  enabled: boolean;
}

interface ChainInfo {
  chain_id: string;
  name: string;
  template_count: number;
  template_ids: string[];
}

interface UseImageGenerationV2Options {
  templateIds?: string[];
  customPrompt?: string;
  timeoutSeconds?: number;
  aspectRatio?: string;
  imageSize?: string;
}

interface UseImageGenerationV2Return {
  processImage: (file: File, aspectRatio?: string, imageSize?: string) => Promise<ProcessResult>;
  isProcessing: boolean;
  elapsedTime: number | null;
  templates: TemplateInfo[];
  chains: ChainInfo[];
  isLoadingTemplates: boolean;
  refreshTemplates: () => Promise<void>;
  error: string | null;
}

export function useImageGenerationV2(
  options: UseImageGenerationV2Options = {}
): UseImageGenerationV2Return {
  const [isProcessing, setIsProcessing] = useState(false);
  const [elapsedTime, setElapsedTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [chains, setChains] = useState<ChainInfo[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);
  
  const { user, refreshProfile } = useAuth();
  const { toast } = useToast();

  const defaultTemplateIds = options.templateIds || [
    'remove_bg',
    'standardize',
    'ecommerce',
    'color_correct'
  ];

  const refreshTemplates = useCallback(async () => {
    setIsLoadingTemplates(true);
    try {
      const [templatesRes, chainsRes] = await Promise.all([
        generationV2API.getTemplates(),
        generationV2API.getChains(),
      ]);
      setTemplates(templatesRes.data || []);
      setChains(chainsRes.data || []);
    } catch (err) {
      console.error('Failed to load templates:', err);
    } finally {
      setIsLoadingTemplates(false);
    }
  }, []);

  const processImage = useCallback(async (file: File, aspectRatio?: string, imageSize?: string): Promise<ProcessResult> => {
    if (!user) {
      const errorMsg = '请先登录';
      setError(errorMsg);
      return { success: false, task_id: null, result_image: null, elapsed_time: null, used_templates: null, error_message: errorMsg };
    }

    if (user.credits < 1) {
      const errorMsg = '积分不足';
      setError(errorMsg);
      return { success: false, task_id: null, result_image: null, elapsed_time: null, used_templates: null, error_message: errorMsg };
    }

    setIsProcessing(true);
    setError(null);
    setElapsedTime(null);

    const startTime = Date.now();

    try {
      const result = await generationV2API.process(file, {
        templateIds: defaultTemplateIds,
        customPrompt: options.customPrompt,
        timeoutSeconds: options.timeoutSeconds || 180,
        aspectRatio: aspectRatio || options.aspectRatio || '1:1',
        imageSize: imageSize || options.imageSize || '1K',
      });

      const elapsed = (Date.now() - startTime) / 1000;
      setElapsedTime(elapsed);

      const data = result.data;

      if (data.success) {
        // Refresh user profile to update credits
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
          used_templates: data.used_templates,
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
          used_templates: null,
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
        used_templates: null,
        error_message: errorMsg,
      };
    } finally {
      setIsProcessing(false);
    }
  }, [user, refreshProfile, defaultTemplateIds, options.customPrompt, options.timeoutSeconds, toast]);

  return {
    processImage,
    isProcessing,
    elapsedTime,
    templates,
    chains,
    isLoadingTemplates,
    refreshTemplates,
    error,
  };
}

