import React from "react";
import { X, Clock, Layers } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProcessingProgressProps {
  progress: number;
  currentStep?: string;
  estimatedRemaining?: number | null;
  onCancel?: () => void;
}

export function ProcessingProgress({
  progress,
  currentStep = "正在处理...",
  estimatedRemaining,
  onCancel,
}: ProcessingProgressProps) {
  // 环形进度条 SVG
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-4 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 rounded-2xl border border-blue-100 dark:border-blue-800/50 animate-fade-in">
      {/* 进度环形 */}
      <div className="relative">
        <svg
          className="w-24 h-24 transform -rotate-90"
          viewBox="0 0 100 100"
        >
          {/* 背景圈 */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-blue-100 dark:text-blue-800/50"
          />
          {/* 进度圈 */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="text-blue-500 transition-all duration-500 ease-out"
            style={{
              filter: "drop-shadow(0 0 6px rgba(59, 130, 246, 0.5))",
            }}
          />
        </svg>
        {/* 百分比文字 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-blue-600 dark:text-blue-400">
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {/* 当前步骤 */}
      <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
        <Layers className="w-4 h-4 animate-pulse" />
        <span className="font-medium">{currentStep}</span>
      </div>

      {/* 预估剩余时间 */}
      {estimatedRemaining !== null && estimatedRemaining !== undefined && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="w-4 h-4" />
          <span>预计剩余: {estimatedRemaining} 秒</span>
        </div>
      )}

      {/* 取消按钮 */}
      {onCancel && (
        <Button
          variant="outline"
          size="sm"
          onClick={onCancel}
          className="mt-2 border-red-200 text-red-600 hover:bg-red-50 hover:border-red-300 dark:border-red-800/50 dark:text-red-400 dark:hover:bg-red-950/30 transition-all duration-200"
        >
          <X className="w-4 h-4 mr-1.5" />
          取消任务
        </Button>
      )}

      {/* 提示信息 */}
      <p className="text-xs text-muted-foreground text-center">
        正在后台处理，您可以继续上传其他图片
      </p>
    </div>
  );
}
