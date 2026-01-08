import React from "react";
import { AlertCircle, RefreshCw, HelpCircle, WifiOff, UploadCloud, Server } from "lucide-react";
import { Button } from "@/components/ui/button";

export type ErrorType = "network" | "upload" | "server" | "credits" | "unknown";

interface ErrorCardProps {
  type?: ErrorType;
  title?: string;
  message: string;
  onRetry?: () => void;
  onHelp?: () => void;
  className?: string;
}

// 错误类型对应的图标和默认标题
const errorConfig: Record<ErrorType, { icon: React.ReactNode; defaultTitle: string }> = {
  network: {
    icon: <WifiOff className="w-10 h-10" />,
    defaultTitle: "网络连接失败",
  },
  upload: {
    icon: <UploadCloud className="w-10 h-10" />,
    defaultTitle: "上传失败",
  },
  server: {
    icon: <Server className="w-10 h-10" />,
    defaultTitle: "服务器错误",
  },
  credits: {
    icon: <AlertCircle className="w-10 h-10" />,
    defaultTitle: "积分不足",
  },
  unknown: {
    icon: <AlertCircle className="w-10 h-10" />,
    defaultTitle: "发生错误",
  },
};

export function ErrorCard({
  type = "unknown",
  title,
  message,
  onRetry,
  onHelp,
  className = "",
}: ErrorCardProps) {
  const config = errorConfig[type];

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`
        flex flex-col items-center gap-4 p-6
        bg-gradient-to-br from-red-50 to-orange-50
        dark:from-red-950/30 dark:to-orange-950/30
        rounded-2xl border border-red-100 dark:border-red-800/50
        animate-fade-in
        ${className}
      `}
    >
      {/* 图标 */}
      <div className="p-4 rounded-full bg-red-100 dark:bg-red-900/30 text-red-500 dark:text-red-400">
        {config.icon}
      </div>

      {/* 标题和消息 */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-red-700 dark:text-red-300 mb-2">
          {title || config.defaultTitle}
        </h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          {message}
        </p>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-3 mt-2">
        {onRetry && (
          <Button
            variant="default"
            size="sm"
            onClick={onRetry}
            className="bg-red-500 hover:bg-red-600 text-white transition-all duration-200"
          >
            <RefreshCw className="w-4 h-4 mr-1.5" />
            重试
          </Button>
        )}
        {onHelp && (
          <Button
            variant="outline"
            size="sm"
            onClick={onHelp}
            className="border-red-200 text-red-600 hover:bg-red-50 dark:border-red-800/50 dark:text-red-400 dark:hover:bg-red-950/30 transition-all duration-200"
          >
            <HelpCircle className="w-4 h-4 mr-1.5" />
            查看帮助
          </Button>
        )}
      </div>

      {/* 错误代码提示 */}
      {type === "network" && (
        <p className="text-xs text-muted-foreground">
          请检查您的网络连接后重试
        </p>
      )}
      {type === "credits" && (
        <p className="text-xs text-muted-foreground">
          请联系客服充值积分
        </p>
      )}
    </div>
  );
}
