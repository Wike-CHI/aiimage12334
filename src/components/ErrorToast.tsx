import { useEffect } from "react";
import { X, AlertCircle, WifiOff, Coins, Image, Server, Upload, HelpCircle } from "lucide-react";
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport } from "@/components/ui/toast";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

// 错误类型配置
const errorTypeConfig: Record<string, { icon: typeof AlertCircle; label: string; color: string; bgColor: string }> = {
  CREDITS_INSUFFICIENT: {
    icon: Coins,
    label: "积分不足",
    color: "text-amber-500",
    bgColor: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
  },
  IMAGE_PROCESSING_FAILED: {
    icon: Image,
    label: "图片处理失败",
    color: "text-red-500",
    bgColor: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  },
  INVALID_IMAGE_FORMAT: {
    icon: Upload,
    label: "不支持的格式",
    color: "text-orange-500",
    bgColor: "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
  },
  IMAGE_TOO_LARGE: {
    icon: Image,
    label: "文件过大",
    color: "text-orange-500",
    bgColor: "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
  },
  NETWORK_ERROR: {
    icon: WifiOff,
    label: "网络错误",
    color: "text-orange-500",
    bgColor: "bg-orange-50 border-orange-200 dark:bg-orange-950/30 dark:border-orange-800",
  },
  API_TIMEOUT: {
    icon: Server,
    label: "请求超时",
    color: "text-yellow-500",
    bgColor: "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800",
  },
  INTERNAL_ERROR: {
    icon: Server,
    label: "服务器错误",
    color: "text-red-500",
    bgColor: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  },
  TASK_NOT_FOUND: {
    icon: HelpCircle,
    label: "任务不存在",
    color: "text-gray-500",
    bgColor: "bg-gray-50 border-gray-200 dark:bg-gray-950/30 dark:border-gray-800",
  },
  VALIDATION_ERROR: {
    icon: AlertCircle,
    label: "验证错误",
    color: "text-yellow-500",
    bgColor: "bg-yellow-50 border-yellow-200 dark:bg-yellow-950/30 dark:border-yellow-800",
  },
  UNKNOWN: {
    icon: AlertCircle,
    label: "处理失败",
    color: "text-red-500",
    bgColor: "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
  },
};

export interface ErrorToastData {
  error_code?: string;
  message: string;
  user_action?: string;
  title?: string;
}

interface ErrorToastProps {
  errors: ErrorToastData[];
  onDismiss?: (index: number) => void;
}

function getErrorDisplay(error_code?: string) {
  if (!error_code) return errorTypeConfig.UNKNOWN;
  return errorTypeConfig[error_code] || errorTypeConfig.UNKNOWN;
}

export function ErrorToast({ errors, onDismiss }: ErrorToastProps) {
  return (
    <ToastProvider>
      {errors.map((error, index) => {
        const errorDisplay = getErrorDisplay(error.error_code);
        const Icon = errorDisplay.icon;

        return (
          <Toast
            key={index}
            variant="destructive"
            className={cn(
              "max-w-md border-2",
              errorDisplay.bgColor
            )}
            duration={error.user_action ? 8000 : 5000} // 有操作建议时显示更长时间
          >
            <div className="flex items-start gap-3">
              <div className={cn("flex-shrink-0 mt-0.5", errorDisplay.color)}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <ToastTitle className={cn("flex items-center gap-2", errorDisplay.color)}>
                  {error.title || errorDisplay.label}
                </ToastTitle>
                <ToastDescription className="mt-1 text-sm text-foreground/90">
                  {error.message}
                </ToastDescription>
                {error.user_action && (
                  <div className="mt-2 p-2 rounded bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-sm flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>{error.user_action}</span>
                  </div>
                )}
              </div>
              {onDismiss && (
                <ToastClose
                  onClick={() => onDismiss(index)}
                  className="flex-shrink-0"
                />
              )}
            </div>
            <ToastViewport />
          </Toast>
        );
      })}
    </ToastProvider>
  );
}

// 全局错误Hook，用于在应用中使用
export function useErrorHandler() {
  const { toast } = useToast();

  const handleError = (error: ErrorToastData) => {
    const errorDisplay = getErrorDisplay(error.error_code);
    const Icon = errorDisplay.icon;

    toast({
      variant: "destructive",
      className: cn("max-w-md border-2", errorDisplay.bgColor),
      duration: error.user_action ? 8000 : 5000,
      title: (
        <div className={cn("flex items-center gap-2", errorDisplay.color)}>
          <Icon className="w-5 h-5" />
          <span>{error.title || errorDisplay.label}</span>
        </div>
      ),
      description: (
        <div className="mt-2">
          <p>{error.message}</p>
          {error.user_action && (
            <div className="mt-2 p-2 rounded bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error.user_action}</span>
            </div>
          )}
        </div>
      ),
    });
  };

  const handleApiError = (response: { success?: boolean; error_code?: string; message?: string; user_action?: string }) => {
    if (response.success === false) {
      handleError({
        error_code: response.error_code,
        message: response.message || "操作失败",
        user_action: response.user_action,
      });
      return true;
    }
    return false;
  };

  return { handleError, handleApiError };
}
