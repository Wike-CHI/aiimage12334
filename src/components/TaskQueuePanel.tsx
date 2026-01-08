import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Circle,
  Clock,
  X,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";

export type TaskStatus = "pending" | "processing" | "completed" | "failed";

interface TaskItem {
  id: string;
  status: TaskStatus;
  progress?: number;
  name?: string;
  error?: string;
}

interface TaskQueuePanelProps {
  tasks: TaskItem[];
  onCancelTask?: (taskId: string) => void;
  onRetryTask?: (taskId: string) => void;
  className?: string;
}

export function TaskQueuePanel({
  tasks,
  onCancelTask,
  onRetryTask,
  className = "",
}: TaskQueuePanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const pendingTasks = tasks.filter((t) => t.status === "pending");
  const processingTasks = tasks.filter((t) => t.status === "processing");
  const completedTasks = tasks.filter((t) => t.status === "completed");
  const failedTasks = tasks.filter((t) => t.status === "failed");

  if (tasks.length === 0) return null;

  return (
    <div
      className={`rounded-2xl border border-border/50 bg-card overflow-hidden animate-fade-in ${className}`}
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
                  className="flex items-center gap-3 p-2 rounded-lg bg-blue-50 dark:bg-blue-950/20"
                >
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {task.name || `任务 #${task.id.slice(-6)}`}
                    </p>
                    {task.progress !== undefined && (
                      <div className="h-1 rounded-full bg-blue-200 dark:bg-blue-800 mt-1 overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                  {onCancelTask && (
                    <button
                      onClick={() => onCancelTask(task.id)}
                      className="p-1 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
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
              {failedTasks.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center gap-3 p-2 rounded-lg bg-red-50 dark:bg-red-950/20"
                >
                  <X className="w-4 h-4 text-red-500" />
                  <p className="flex-1 text-sm truncate text-red-600 dark:text-red-400">
                    {task.name || `任务 #${task.id.slice(-6)}`}
                  </p>
                  {onRetryTask && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRetryTask(task.id)}
                      className="text-red-600 hover:text-red-700 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30"
                    >
                      重试
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
