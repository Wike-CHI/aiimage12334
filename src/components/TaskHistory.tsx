import { useState } from "react";
import { format } from "date-fns";
import { zhCN } from "date-fns/locale";
import { Download, Trash2, Eye, Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";
import { cn } from "@/lib/utils";

interface Task {
  id: string;
  original_image_url: string | null;
  processed_image_url: string | null;
  status: string;
  resolution: string;
  ratio: string;
  error_message: string | null;
  created_at: string;
}

interface TaskHistoryProps {
  tasks: Task[];
  onRefresh: () => void;
  onSelect: (task: Task) => void;
}

const statusConfig: Record<string, { icon: typeof Clock; label: string; color: string; animate?: boolean }> = {
  pending: { icon: Clock, label: "等待中", color: "text-amber-500" },
  processing: { icon: Loader2, label: "处理中", color: "text-blue-500", animate: true },
  completed: { icon: CheckCircle, label: "已完成", color: "text-green-500" },
  failed: { icon: XCircle, label: "失败", color: "text-destructive" },
};

export function TaskHistory({ tasks, onRefresh, onSelect }: TaskHistoryProps) {
  const [previewImage, setPreviewImage] = useState<{ src: string; title: string } | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { toast } = useToast();

  const handleDelete = async (taskId: string) => {
    setDeletingId(taskId);
    try {
      const { error } = await supabase
        .from("generation_tasks")
        .delete()
        .eq("id", taskId);

      if (error) throw error;

      toast({ title: "删除成功" });
      onRefresh();
    } catch (error) {
      toast({
        title: "删除失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = (url: string) => {
    const link = document.createElement("a");
    link.href = url;
    link.download = `white-bg-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
            const status = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.pending;
            const StatusIcon = status.icon;

            return (
              <div
                key={task.id}
                className="flex items-center gap-4 p-3 rounded-xl bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors"
              >
                {/* Thumbnail */}
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
                    <StatusIcon className={cn("w-4 h-4", status.color, status.animate && "animate-spin")} />
                    <span className={cn("text-sm font-medium", status.color)}>{status.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {format(new Date(task.created_at), "MM月dd日 HH:mm", { locale: zhCN })}
                  </p>
                  {task.resolution !== "original" && (
                    <p className="text-xs text-muted-foreground">{task.resolution}</p>
                  )}
                  {task.error_message && (
                    <p className="text-xs text-destructive truncate">{task.error_message}</p>
                  )}
                </div>

                {/* Result thumbnail */}
                {task.processed_image_url && (
                  <div
                    className="w-16 h-16 rounded-lg overflow-hidden bg-white border border-border flex-shrink-0 cursor-pointer"
                    onClick={() => setPreviewImage({ src: task.processed_image_url!, title: "白底图" })}
                  >
                    <img
                      src={task.processed_image_url}
                      alt="Processed"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col gap-1">
                  {task.processed_image_url && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleDownload(task.processed_image_url!)}
                    >
                      <Download className="w-4 h-4" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDelete(task.id)}
                    disabled={deletingId === task.id}
                  >
                    {deletingId === task.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Preview Dialog */}
      <Dialog open={!!previewImage} onOpenChange={() => setPreviewImage(null)}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 bg-background/95 backdrop-blur-sm border-border">
          <div className="relative w-full h-full flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <h3 className="font-medium text-foreground">{previewImage?.title}</h3>
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
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}