import { Download, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ImagePreviewProps {
  originalImage: string | null;
  processedImage: string | null;
  isProcessing: boolean;
  onClear: () => void;
  onDownload: () => void;
}

export function ImagePreview({ 
  originalImage, 
  processedImage, 
  isProcessing, 
  onClear,
  onDownload 
}: ImagePreviewProps) {
  return (
    <div className="w-full animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Original Image */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">原图</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="h-8 px-2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4 mr-1" />
              清除
            </Button>
          </div>
          <div className="relative aspect-square rounded-xl overflow-hidden bg-secondary/50 border border-border">
            {originalImage && (
              <img
                src={originalImage}
                alt="Original"
                className="w-full h-full object-contain"
              />
            )}
          </div>
        </div>

        {/* Processed Image */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground">白底图</h3>
            {processedImage && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onDownload}
                className="h-8 px-2 text-primary hover:text-primary"
              >
                <Download className="w-4 h-4 mr-1" />
                下载
              </Button>
            )}
          </div>
          <div className={cn(
            "relative aspect-square rounded-xl overflow-hidden border border-border",
            processedImage ? "bg-white" : "bg-secondary/50"
          )}>
            {isProcessing ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                <div className="relative">
                  <RefreshCw className="w-8 h-8 text-primary animate-spin" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-foreground">AI 处理中...</p>
                  <p className="text-xs text-muted-foreground mt-1">正在生成白底图</p>
                </div>
                <div className="w-32 h-1 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full animate-pulse-soft" style={{ width: '60%' }} />
                </div>
              </div>
            ) : processedImage ? (
              <img
                src={processedImage}
                alt="Processed"
                className="w-full h-full object-contain animate-scale-in"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                <p className="text-sm">等待生成</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
