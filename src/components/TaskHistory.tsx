import { useState } from "react";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";
import { Download, Eye, Clock, CheckCircle, XCircle, ArrowLeft, Play, Trash2, Ban, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { generationAPI, generationV2API } from "@/integrations/api/client";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";

interface Task {
  id: number;
  user_id: number;
  original_image_url: string | null;
  result_image_url: string | null;
  status: string;
  credits_used: number;
  width: number;
  height: number;
  error_message?: string | null;
  error_code?: string | null;
  user_action?: string | null;
  created_at: string;
}

interface TaskHistoryProps {
  tasks: Task[];
  onRefresh: () => void;
  onSelect: (task: Task) => void;
}

const statusConfig: Record<string, { icon: typeof Clock; label: string; color: string }> = {
  PENDING: { icon: Clock, label: "等待中", color: "text-amber-500" },
  PROCESSING: { icon: Clock, label: "处理中", color: "text-blue-500" },
  COMPLETED: { icon: CheckCircle, label: "已完成", color: "text-green-500" },
  FAILED: { icon: XCircle, label: "失败", color: "text-destructive" },
};

// 错误类型配置
const errorTypeConfig: Record<string, { label: string; color: string; icon: string }> = {
  CREDITS_INSUFFICIENT: { label: "积分不足", color: "bg-amber-100 text-amber-700 border-amber-300", icon: "💰" },
  IMAGE_PROCESSING_FAILED: { label: "处理失败", color: "bg-red-100 text-red-700 border-red-300", icon: "🖼️" },
  INVALID_IMAGE_FORMAT: { label: "格式错误", color: "bg-orange-100 text-orange-700 border-orange-300", icon: "📁" },
  IMAGE_TOO_LARGE: { label: "文件过大", color: "bg-orange-100 text-orange-700 border-orange-300", icon: "📦" },
  NETWORK_ERROR: { label: "网络错误", color: "bg-orange-100 text-orange-700 border-orange-300", icon: "🌐" },
  API_TIMEOUT: { label: "超时", color: "bg-yellow-100 text-yellow-700 border-yellow-300", icon: "⏱️" },
  INTERNAL_ERROR: { label: "服务器错误", color: "bg-red-100 text-red-700 border-red-300", icon: "⚙️" },
  TASK_NOT_FOUND: { label: "任务丢失", color: "bg-gray-100 text-gray-700 border-gray-300", icon: "❓" },
  UNKNOWN: { label: "处理失败", color: "bg-red-100 text-red-700 border-red-300", icon: "❌" },
};

function getErrorDisplay(error_code?: string | null) {
  if (!error_code) return errorTypeConfig.UNKNOWN;
  return errorTypeConfig[error_code] || errorTypeConfig.UNKNOWN;
}

// 解析错误消息，尝试提取错误码
function parseErrorCode(error_message?: string | null): { code: string | null; message: string } {
  if (!error_message) return { code: null, message: "未知错误" };

  // 尝试匹配常见的错误码模式
  const codePatterns = [
    { pattern: /CREDITS_INSUFFICIENT/i, code: "CREDITS_INSUFFICIENT" },
    { pattern: /IMAGE_PROCESSING_FAILED/i, code: "IMAGE_PROCESSING_FAILED" },
    { pattern: /INVALID_IMAGE_FORMAT/i, code: "INVALID_IMAGE_FORMAT" },
    { pattern: /IMAGE_TOO_LARGE/i, code: "IMAGE_TOO_LARGE" },
    { pattern: /NETWORK_ERROR/i, code: "NETWORK_ERROR" },
    { pattern: /API_TIMEOUT|TIMEOUT/i, code: "API_TIMEOUT" },
    { pattern: /INTERNAL_ERROR/i, code: "INTERNAL_ERROR" },
    { pattern: /TASK_NOT_FOUND/i, code: "TASK_NOT_FOUND" },
  ];

  for (const { pattern, code } of codePatterns) {
    if (pattern.test(error_message)) {
      return { code, message: error_message };
    }
  }

  return { code: null, message: error_message };
}

export function TaskHistory({ tasks, onRefresh, onSelect }: TaskHistoryProps) {
  const [previewImage, setPreviewImage] = useState<{ src: string; title: string } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [loadingTasks, setLoadingTasks] = useState<Set<number>>(new Set());
  const { toast } = useToast();
  const { user, refreshProfile } = useAuth();

  const isActiveTask = (status: string) =>
    status.toUpperCase() === "PENDING" || status.toUpperCase() === "PROCESSING";
  const isCompletedTask = (status: string) => status.toUpperCase() === "COMPLETED";
  const isFailedTask = (status: string) =>
    status.toUpperCase() === "FAILED" || status.toUpperCase() === "CANCELLED";

  const handleDownload = async (url: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `white-bg-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch {
      window.open(url, '_blank');
    }
  };

  const handleRetry = async (task: Task) => {
    if (!task.original_image_url) {
      toast({
        title: "无法重试",
        description: "原图不存在",
        variant: "destructive"
      });
      return;
    }

    if (!user || user.credits < 1) {
      toast({
        title: "积分不足",
        description: "请充值后重试",
        variant: "destructive"
      });
      return;
    }

    setLoadingTasks(prev => new Set(prev).add(task.id));

    try {
      // 使用 V2 同步接口重新生成
      const response = await fetch(task.original_image_url);
      const blob = await response.blob();
      const file = new File([blob], "retry.png", { type: "image/png" });

      const result = await generationV2API.process(file, {
        templateIds: ['remove_bg', 'standardize', 'ecommerce', 'color_correct']
      });

      if (result.data.success) {
        toast({
          title: "重新生成成功",
          description: `新图片已生成，耗时 ${result.data.elapsed_time} 秒`,
        });
        await refreshProfile();
        onRefresh();
      } else {
        throw new Error(result.data.error_message || "生成失败");
      }
    } catch (error) {
      toast({
        title: "重试失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive"
      });
    } finally {
      setLoadingTasks(prev => {
        const next = new Set(prev);
        next.delete(task.id);
        return next;
      });
    }
  };

  const handleCancel = async (taskId: number) => {
    if (!confirm("确定要取消这个任务吗？")) return;

    setLoadingTasks(prev => new Set(prev).add(taskId));
    try {
      await generationAPI.cancelTask(taskId);
      toast({ title: "已取消", description: "任务已停止" });
      onRefresh();
    } catch (error) {
      toast({
        title: "操作失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive"
      });
    } finally {
      setLoadingTasks(prev => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  const handleDelete = async (taskId: number) => {
    if (!confirm("确定要删除这个任务吗？删除后无法恢复。")) return;

    setLoadingTasks(prev => new Set(prev).add(taskId));
    try {
      await generationAPI.deleteTask(taskId);
      toast({ title: "已删除", description: "任务已从历史记录中移除" });
      onRefresh();
    } catch (error) {
      toast({
        title: "操作失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive"
      });
    } finally {
      setLoadingTasks(prev => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>暂无历史记录</p>
        <p className="text-sm mt-1">生成白底图后将在这里显示</p>
        <p className="text-xs mt-2 text-amber-500">使用 V2 异步接口，生成完成后自动刷新</p>
      </div>
    );
  }

  return (
    <>
      {/* Refresh Button */}
      <div className="flex justify-end mb-4">
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </Button>
      </div>

      <ScrollArea className="h-[400px]">
        <div className="space-y-3 pr-4">
          {tasks.map((task) => {
            const status = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.PENDING;
            const StatusIcon = status.icon;
            const resolution = `${task.width}x${task.height}`;
            const isLoading = loadingTasks.has(task.id);

            return (
              <div
                key={task.id}
                className="flex items-center gap-4 p-3 rounded-xl bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors"
              >
                {/* Original Image Thumbnail */}
                <div
                  className="w-16 h-16 rounded-lg overflow-hidden bg-secondary flex-shrink-0 cursor-pointer"
                  onClick={() => task.original_image_url && setPreviewImage({ src: task.original_image_url, title: "原图" })}
                >
                  {task.original_image_url ? (
                    <img
                      src={task.original_image_url}
                      alt="Original"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.parentElement?.insertAdjacentHTML(
                          'afterbegin',
                          '<div class="w-full h-full flex items-center justify-center text-muted-foreground"><Eye class="w-5 h-5" /></div>'
                        );
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                      <Eye className="w-5 h-5" />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusIcon className={cn("w-4 h-4", status.color)} />
                    <span className={cn("text-sm font-medium", status.color)}>{status.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {format(new Date(task.created_at), "MM月dd日 HH:mm", { locale: zhCN })}
                  </p>
                  <p className="text-xs text-muted-foreground">{resolution}</p>

                  {/* 错误信息展示 */}
                  {(task.error_message || isFailedTask(task.status)) && (
                    <div className="mt-1.5">
                      {/* 错误类型标签 */}
                      {(task.error_code || isFailedTask(task.status)) && (() => {
                        const errorDisplay = getErrorDisplay(task.error_code || null);
                        const parsed = parseErrorCode(task.error_message);
                        const errorCode = task.error_code || parsed.code;

                        return (
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="text-xs">{errorDisplay.icon}</span>
                            <Badge
                              variant="outline"
                              className={cn("text-xs px-1.5 py-0 h-5", errorDisplay.color)}
                            >
                              {errorDisplay.label}
                            </Badge>
                          </div>
                        );
                      })()}

                      {/* 错误消息 */}
                      {task.error_message && (
                        <p className="text-xs text-destructive line-clamp-2" title={task.error_message}>
                          {task.error_message}
                        </p>
                      )}

                      {/* 用户操作建议 */}
                      {task.user_action && (
                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-1 flex items-center gap-1">
                          <AlertCircle className="w-3 h-3 flex-shrink-0" />
                          <span>{task.user_action}</span>
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Result thumbnail */}
                {task.result_image_url && (
                  <div
                    className="w-16 h-16 rounded-lg overflow-hidden bg-white border border-border flex-shrink-0 cursor-pointer"
                    onClick={() => setPreviewImage({ src: task.result_image_url!, title: "白底图" })}
                  >
                    <img
                      src={task.result_image_url}
                      alt="Processed"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        e.currentTarget.parentElement?.insertAdjacentHTML(
                          'afterbegin',
                          '<div class="w-full h-full flex items-center justify-center text-muted-foreground"><Eye class="w-5 h-5" /></div>'
                        );
                      }}
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col gap-1">
                  {task.result_image_url && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleDownload(task.result_image_url!)}
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  )}

                  {/* Cancel button for active tasks */}
                  {isActiveTask(task.status) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-amber-500"
                      onClick={() => handleCancel(task.id)}
                      disabled={isLoading}
                    >
                      <Ban className="w-4 h-4" />
                    </Button>
                  )}

                  {/* Retry button for failed tasks */}
                  {isFailedTask(task.status) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-blue-500"
                      onClick={() => handleRetry(task)}
                      disabled={isLoading}
                    >
                      <Play className="w-4 h-4" />
                    </Button>
                  )}

                  {/* Delete button for completed or failed tasks */}
                  {(isCompletedTask(task.status) || isFailedTask(task.status)) && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => handleDelete(task.id)}
                      disabled={isLoading}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* V2 Info Banner */}
      <div className="mt-4 p-3 rounded-lg bg-blue-50 border border-blue-200">
        <p className="text-xs text-blue-600 text-center">
          提示: 新生成的白底图将自动刷新，无需手动刷新
        </p>
      </div>

      {/* Preview Dialog */}
      <Dialog open={!!previewImage} onOpenChange={() => { setPreviewImage(null); setIsFullscreen(false); }}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 bg-background/95 backdrop-blur-sm border-border">
          <DialogHeader>
            <DialogTitle className="sr-only">{previewImage?.title || "图片预览"}</DialogTitle>
            <DialogDescription className="sr-only">
              {previewImage?.title === "白底图" ? "生成的白底图预览" : "原图预览"}
            </DialogDescription>
          </DialogHeader>
          <div className="relative w-full h-full flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              {isFullscreen ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsFullscreen(false)}
                  className="h-8 px-2"
                >
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  返回
                </Button>
              ) : (
                <h3 className="font-medium text-foreground">{previewImage?.title}</h3>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => { setPreviewImage(null); setIsFullscreen(false); }}
                className="h-8 w-8"
              >
                <XCircle className="w-4 h-4" />
              </Button>
            </div>
            <div className="flex-1 p-4 flex items-center justify-center overflow-auto">
              {previewImage && (
                <img
                  src={previewImage.src}
                  alt={previewImage.title}
                  className="max-w-full max-h-[75vh] object-contain rounded-lg"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              )}
            </div>
            {/* Download button for result images */}
            {previewImage && previewImage.title === "白底图" && (
              <div className="flex justify-center pb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload(previewImage.src)}
                  className="gap-2"
                >
                  <Download className="w-4 h-4" />
                  下载图片
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
