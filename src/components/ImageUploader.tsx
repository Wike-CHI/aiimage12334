import { useState, useCallback } from "react";
import { Upload, Image as ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface ImageUploaderProps {
  onImageSelect: (imageBase64: string) => void;
  disabled?: boolean;
}

export function ImageUploader({ onImageSelect, disabled }: ImageUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) {
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      onImageSelect(result);
    };
    reader.readAsDataURL(file);
  }, [onImageSelect]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;
    
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile, disabled]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = useCallback(() => {
    if (disabled) return;
    
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        handleFile(file);
      }
    };
    input.click();
  }, [handleFile, disabled]);

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={cn(
        "relative flex flex-col items-center justify-center w-full min-h-[280px] rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer group",
        isDragging 
          ? "border-primary bg-primary/5 scale-[1.02]" 
          : "border-border hover:border-primary/50 hover:bg-secondary/50",
        disabled && "opacity-50 cursor-not-allowed pointer-events-none"
      )}
    >
      <div className={cn(
        "flex flex-col items-center gap-4 transition-transform duration-300",
        isDragging && "scale-110"
      )}>
        <div className={cn(
          "p-4 rounded-2xl transition-all duration-300",
          isDragging 
            ? "bg-primary text-primary-foreground" 
            : "bg-secondary text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
        )}>
          {isDragging ? (
            <ImageIcon className="w-8 h-8" />
          ) : (
            <Upload className="w-8 h-8" />
          )}
        </div>
        
        <div className="text-center">
          <p className="font-medium text-foreground">
            {isDragging ? "释放图片" : "拖拽图片到这里"}
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            或点击选择文件
          </p>
        </div>
        
        <p className="text-xs text-muted-foreground">
          支持 JPG, PNG, WebP 格式
        </p>
      </div>
    </div>
  );
}
