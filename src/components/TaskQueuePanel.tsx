import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Circle,
  Clock,
  X,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

interface TaskItem {
  id: string;
  status: TaskStatus;
  progress?: number;
  name?: string;
  error?: string;
  error_code?: string;
  user_action?: string;
}

interface TaskQueuePanelProps {
  tasks: TaskItem[];
  onCancelTask?: (taskId: string) => void;
  onRetryTask?: (taskId: string) => void;
  className?: string;
}

// 处理步骤配置
const PROCESSING_STEPS = [
  { id: "remove_bg", name: "去背景" },
  { id: "standardize", name: "标准化" },
  { id: "ecommerce", name: "电商优化" },
  { id: "color_correct", name: "色彩校正" },
];

// 获取当前处理步骤名称
function getCurrentStep(progress?: number): string {
  if (progress === undefined) return "";
  const stepCount = PROCESSING_STEPS.length;
  const perStep = 100 / stepCount;
  const currentStepIndex = Math.min(Math.floor(progress / perStep), stepCount - 1);
  return PROCESSING_STEPS[currentStepIndex]?.name || "";
}

// 错误类型配置
const errorTypeConfig = {
  CREDITS_INSUFFICIENT: { label: "积分不足", color: "text-amber-500", icon: "💰" },
  IMAGE_PROCESSING_FAILED: { label: "处理失败", color: "text-red-500", icon: "🖼️" },
  INVALID_IMAGE_FORMAT: { label: "格式错误", color: "text-orange-500", icon: "📁" },
  IMAGE_TOO_LARGE: { label: "文件过大", color: "text-orange-500", icon: "📦" },
  NETWORK_ERROR: { label: "网络错误", color: "text-orange-500", icon: "🌐" },
  API_TIMEOUT: { label: "超时", color: "text-yellow-500", icon: "⏱️" },
  INTERNAL_ERROR: { label: "服务器错误", color: "text-red-500", icon: "⚙️" },
  TASK_NOT_FOUND: { label: "任务丢失", color: "text-gray-500", icon: "❓" },
  UNKNOWN: { label: "处理失败", color: "text-red-500", icon: "❌" },
};

function getErrorDisplay(error_code?: string) {
  if (!error_code) return errorTypeConfig.UNKNOWN;
  return errorTypeConfig[error_code as keyof typeof errorTypeConfig] || errorTypeConfig.UNKNOWN;
}

export function TaskQueuePanel({
  tasks,
  onCancelTask,
  onRetryTask,
  className = "",
}: TaskQueuePanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [expandedError, setExpandedError] = useState<string | null>(null);

  const pendingTasks = tasks.filter((t) => t.status === "pending");
  const processingTasks = tasks.filter((t) => t.status === "processing");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const failedTasks = tasks.filter((t) => t.status === "failed");

  console.log('[TaskQueuePanel] 渲染任务列表:', {
    totalTasks: tasks.length,
    pendingCount: pendingTasks.length,
    processingCount: processingTasks.length,
    completedCount: completedTasks.length,
    failedCount: failedTasks.length,
    tasks: tasks.map(t => ({ id: t.id, status: t.status, progress: t.progress }))
  });

  if (tasks.length === 0) return null;

  return (
    <div
      className={cn(
        "rounded-2xl border border-border/50 bg-card overflow-hidden animate-fade-in",
        className
      )}
    >
      {/* 头部 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium text-sm">处理队列</span>
          <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs">
            {tasks.length}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* 展开内容 */}
      {isExpanded && (
        <div className="border-t border-border/50">
          {/* 处理中任务 */}
          {processingTasks.length > 0 && (
            <div className="p-3 border-b border-border/50">
              <p className="text-xs text-muted-foreground mb-2 font-medium">
                正在处理 ({processingTasks.length})
              </p>
              {processingTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20"
                >
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {task.name || `任务 #${task.id.slice(-6)}`}
                    </p>
                    {task.progress !== undefined && (
                      <>
                        {/* 进度条 */}
                        <div className="h-1.5 rounded-full bg-blue-200 dark:bg-blue-800 mt-2 overflow-hidden">
                          <div
                            className="h-full bg-blue-500 transition-all duration-300 animate-stripes"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                        {/* 处理步骤指示 */}
                        <div className="flex items-center justify-between mt-1.5 text-xs text-blue-600 dark:text-blue-400">
                          <span>{getCurrentStep(task.progress)}中...</span>
                          <span>{task.progress}%</span>
                        </div>
                      </>
                    )}
                  </div>
                  {onCancelTask && (
                    <button
                      onClick={() => onCancelTask(task.id)}
                      className="p-1.5 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                      aria-label="取消任务"
                    >
                      <X className="w-4 h-4 text-blue-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 等待中任务 */}
          {pendingTasks.length > 0 && (
            <div className="p-3 border-b border-border/50">
              <p className="text-xs text-muted-foreground mb-2 font-medium">
                等待中 ({pendingTasks.length})
              </p>
              {pendingTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-2 rounded-lg bg-muted/50"
                >
                  <Circle className="w-4 h-4 text-muted-foreground" />
                  <p className="flex-1 text-sm truncate">
                    {task.name || `任务 #${task.id.slice(-6)}`}
                  </p>
                  {onCancelTask && (
                    <button
                      onClick={() => onCancelTask(task.id)}
                      className="p-1 rounded hover:bg-muted transition-colors"
                      aria-label="取消任务"
                    >
                      <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 已完成任务 */}
          {completedTasks.length > 0 && (
            <div className="p-3 border-b border-border/50">
              <p className="text-xs text-muted-foreground mb-2 font-medium">
                已完成 ({completedTasks.length})
              </p>
              {completedTasks.slice(0, 3).map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-2 rounded-lg"
                >
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <p className="flex-1 text-sm truncate text-muted-foreground">
                    {task.name || `任务 #${task.id.slice(-6)}`}
                  </p>
                </div>
              ))}
              {completedTasks.length > 3 && (
                <p className="text-xs text-muted-foreground pl-7">
                  还有 {completedTasks.length - 3} 个任务已完成
                </p>
              )}
            </div>
          )}

          {/* 失败任务 */}
          {failedTasks.length > 0 && (
            <div className="p-3">
              <p className="text-xs text-muted-foreground mb-2 font-medium">
                失败 ({failedTasks.length})
              </p>
              {failedTasks.map((task) => {
                const errorDisplay = getErrorDisplay(task.error_code);
                const isExpanded = expandedError === task.id;

                return (
                  <div
                    key={task.id}
                    className="flex flex-col gap-1 p-2 rounded-lg bg-red-50 dark:bg-red-950/20"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm">{errorDisplay.icon}</span>
                      <X className="w-4 h-4 text-red-500 flex-shrink-0" />
                      <p className="flex-1 text-sm truncate text-red-600 dark:text-red-400">
                        {task.name || `任务 #${task.id.slice(-6)}`}
                      </p>
                      <button
                        onClick={() => setExpandedError(isExpanded ? null : task.id)}
                        className="text-xs text-red-500 hover:text-red-600 underline"
                      >
                        {isExpanded ? "收起" : "详情"}
                      </button>
                    </div>

                    {/* 错误详情展开区域 */}
                    {isExpanded && (
                      <div
                        className="mt-2 p-2 rounded bg-red-100/50 dark:bg-red-900/30 text-xs"
                        role="alert"
                      >
                        <p className={cn("font-medium mb-1", errorDisplay.color)}>
                          {errorDisplay.label}
                        </p>
                        <p className="text-red-700 dark:text-red-300 mb-1">
                          {task.error || "未知错误"}
                        </p>
                        {task.user_action && (
                          <p className="text-blue-600 dark:text-blue-400 mt-2">
                            💡 {task.user_action}
                          </p>
                        )}
                        {onRetryTask && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onRetryTask(task.id)}
                            className="mt-2 h-7 text-xs border-red-300 text-red-600 hover:bg-red-100"
                          >
                            <RefreshCw className="w-3 h-3 mr-1" />
                            重试
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
