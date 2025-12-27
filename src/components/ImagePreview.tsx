import { useState } from "react";
import { Download, RefreshCw, X, ZoomIn, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
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
  const [previewImage, setPreviewImage] = useState<{ src: string; title: string } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  return (
    <>
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
            <div 
              className="relative aspect-square rounded-xl overflow-hidden bg-secondary/50 border border-border group cursor-pointer"
              onClick={() => originalImage && setPreviewImage({ src: originalImage, title: "原图" })}
            >
              {originalImage && (
                <>
                  <img
                    src={originalImage}
                    alt="Original"
                    className="w-full h-full object-contain"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                    <ZoomIn className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </>
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
            <div 
              className={cn(
                "relative aspect-square rounded-xl overflow-hidden border border-border group",
                processedImage ? "bg-white cursor-pointer" : "bg-secondary/50"
              )}
              onClick={() => processedImage && setPreviewImage({ src: processedImage, title: "白底图" })}
            >
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
                <>
                  <img
                    src={processedImage}
                    alt="Processed"
                    className="w-full h-full object-contain animate-scale-in"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                    <ZoomIn className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                  <p className="text-sm">等待生成</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Lightbox Preview Dialog */}
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
                <X className="w-4 h-4" />
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
            {/* Download button in preview */}
            {previewImage && previewImage.title === "白底图" && (
              <div className="flex justify-center pb-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onDownload}
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
