import { useState, useCallback } from "react";
import { Sparkles } from "lucide-react";
import { ImageUploader } from "@/components/ImageUploader";
import { ImagePreview } from "@/components/ImagePreview";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";

const Index = () => {
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const { toast } = useToast();

  const handleImageSelect = useCallback((imageBase64: string) => {
    setOriginalImage(imageBase64);
    setProcessedImage(null);
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!originalImage) return;

    setIsProcessing(true);
    setProcessedImage(null);

    try {
      const { data, error } = await supabase.functions.invoke("generate-white-bg", {
        body: { imageBase64: originalImage },
      });

      if (error) {
        throw new Error(error.message || "处理失败");
      }

      if (data.error) {
        throw new Error(data.error);
      }

      if (data.image) {
        setProcessedImage(data.image);
        toast({
          title: "生成成功",
          description: "白底图已生成完成",
        });
      } else {
        throw new Error("未能生成图片");
      }
    } catch (error) {
      console.error("Error generating white background:", error);
      toast({
        title: "生成失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
    }
  }, [originalImage, toast]);

  const handleClear = useCallback(() => {
    setOriginalImage(null);
    setProcessedImage(null);
  }, []);

  const handleDownload = useCallback(() => {
    if (!processedImage) return;

    const link = document.createElement("a");
    link.href = processedImage;
    link.download = `white-bg-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast({
      title: "下载成功",
      description: "图片已保存到本地",
    });
  }, [processedImage, toast]);

  return (
    <div className="min-h-screen gradient-subtle">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl gradient-primary">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-display font-semibold text-lg">白底图生成器</span>
          </div>
          <p className="text-sm text-muted-foreground hidden sm:block">
            AI 智能抠图 · 一键生成
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container max-w-5xl mx-auto px-4 py-8 md:py-12">
        {/* Hero Section */}
        <div className="text-center mb-10 md:mb-14">
          <h1 className="font-display text-3xl md:text-4xl lg:text-5xl font-bold text-foreground mb-4 tracking-tight">
            AI 白底图生成
          </h1>
          <p className="text-muted-foreground text-base md:text-lg max-w-xl mx-auto">
            上传任意图片，AI 智能识别主体，自动生成纯白背景图片
          </p>
        </div>

        {/* Upload / Preview Area */}
        <div className="max-w-4xl mx-auto">
          <div className="surface-elevated rounded-2xl shadow-medium p-6 md:p-8 border border-border/50">
            {!originalImage ? (
              <ImageUploader 
                onImageSelect={handleImageSelect} 
                disabled={isProcessing}
              />
            ) : (
              <div className="space-y-6">
                <ImagePreview
                  originalImage={originalImage}
                  processedImage={processedImage}
                  isProcessing={isProcessing}
                  onClear={handleClear}
                  onDownload={handleDownload}
                />
                
                {/* Action Button */}
                {!processedImage && (
                  <div className="flex justify-center pt-2">
                    <Button
                      onClick={handleGenerate}
                      disabled={isProcessing}
                      size="lg"
                      className="px-8 h-12 text-base font-medium gradient-primary hover:opacity-90 transition-opacity"
                    >
                      {isProcessing ? (
                        <>处理中...</>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5 mr-2" />
                          生成白底图
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-10">
            {[
              { title: "智能抠图", desc: "AI 精准识别图片主体" },
              { title: "纯白背景", desc: "生成干净的白底图片" },
              { title: "高清输出", desc: "保持原图清晰度" },
            ].map((feature, i) => (
              <div 
                key={i}
                className="text-center p-5 rounded-xl bg-card border border-border/50 shadow-soft"
              >
                <h3 className="font-display font-semibold text-foreground mb-1">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {feature.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-auto">
        <div className="container max-w-5xl mx-auto px-4 py-6 text-center">
          <p className="text-sm text-muted-foreground">
            Powered by Gemini 3 Pro Image
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
