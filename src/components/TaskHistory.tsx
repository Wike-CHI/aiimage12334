import { useState } from "react";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";
import { Download, Eye, Clock, CheckCircle, XCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

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

export function TaskHistory({ tasks, onRefresh, onSelect }: TaskHistoryProps) {
  const [previewImage, setPreviewImage] = useState<{ src: string; title: string } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

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
      // Fallback: open in new tab
      window.open(url, '_blank');
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>暂无历史记录</p>
        <p className="text-sm mt-1">生成白底图后将在这里显示</p>
      </div>
    );
  }

  return (
    <>
      <ScrollArea className="h-[400px]">
        <div className="space-y-3 pr-4">
          {tasks.map((task) => {
            const status = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.PENDING;
            const StatusIcon = status.icon;
            const resolution = `${task.width}x${task.height}`;

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
                  {task.error_message && (
                    <p className="text-xs text-destructive truncate">{task.error_message}</p>
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
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Preview Dialog */}
      <Dialog open={!!previewImage} onOpenChange={() => { setPreviewImage(null); setIsFullscreen(false); }}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 bg-background/95 backdrop-blur-sm border-border">
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
