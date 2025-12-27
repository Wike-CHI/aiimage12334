import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, History, Upload } from "lucide-react";
import { ImageUploader } from "@/components/ImageUploader";
import { ImagePreview } from "@/components/ImagePreview";
import { TaskHistory } from "@/components/TaskHistory";
import { UserMenu } from "@/components/UserMenu";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { useTaskHistory } from "@/hooks/useTaskHistory";
import { useUploadImageCache } from "@/hooks/useImageCache";
import { useTaskImageCache } from "@/hooks/useImageCache";
import { generationAPI } from "@/integrations/api/client";

const RESOLUTIONS = [
  { value: 0, label: "原始尺寸" },
  { value: 1024, label: "1024px" },
  { value: 1280, label: "1280px" },
  { value: 2048, label: "2048px" },
];

const RATIOS = [
  { value: "original", label: "原始比例" },
  { value: "1:1", label: "1:1 正方形" },
  { value: "3:4", label: "3:4 竖版" },
  { value: "4:3", label: "4:3 横版" },
  { value: "9:16", label: "9:16 手机屏" },
  { value: "16:9", label: "16:9 横屏" },
];

const Index = () => {
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [originalCacheKey, setOriginalCacheKey] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [processedCacheKey, setProcessedCacheKey] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [resolution, setResolution] = useState<number>(0);
  const [ratio, setRatio] = useState("original");
  const [activeTab, setActiveTab] = useState("generate");
  const { toast } = useToast();
  const { user, refreshProfile } = useAuth();
  const { tasks, refetch: refetchTasks } = useTaskHistory();
  const { getCachedImage } = useUploadImageCache();
  const { cacheTaskImage } = useTaskImageCache();
  const navigate = useNavigate();

  const handleImageSelect = useCallback(async (imageBase64: string, cacheKey?: string) => {
    setOriginalImage(imageBase64);
    setOriginalCacheKey(cacheKey || null);
    setProcessedImage(null);
    setProcessedCacheKey(null);
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!originalImage) return;

    if (!user) {
      toast({
        title: "请先登录",
        description: "登录后即可使用白底图生成功能",
        variant: "destructive",
      });
      navigate("/auth");
      return;
    }

    if (!user || user.credits < 1) {
      toast({
        title: "积分不足",
        description: "您的积分已用完，请充值后继续使用",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);
    setProcessedImage(null);

    try {
      // 将 base64 转换为 File
      const response = await fetch(originalImage);
      const blob = await response.blob();
      const file = new File([blob], "image.png", { type: "image/png" });

      // 解析分辨率 (0=原始尺寸)
      const size = resolution || 1024;
      const result = await generationAPI.generate(file, size, size, ratio);

      if (result.data && result.data.result_image_url) {
        setProcessedImage(result.data.result_image_url);

        // Cache the processed image
        const taskId = result.data.id || Date.now();
        const newCacheKey = `task:${taskId}`;
        await cacheTaskImage(taskId, blob, size, size);
        setProcessedCacheKey(newCacheKey);

        // Refresh profile to update credits display
        await refreshProfile();
        // Refresh tasks to show new history
        refetchTasks();
        toast({
          title: "生成成功",
          description: `白底图已生成，剩余积分: ${(user?.credits ?? 1) - 1}`,
        });
      } else {
        throw new Error(result.data?.error || "未能生成图片");
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
  }, [originalImage, toast, user, refreshProfile, navigate, resolution, ratio, refetchTasks, cacheTaskImage]);

  const handleClear = useCallback(() => {
    setOriginalImage(null);
    setOriginalCacheKey(null);
    setProcessedImage(null);
    setProcessedCacheKey(null);
  }, []);

  const handleDownload = useCallback(async () => {
    if (!processedImage) return;

    try {
      // Fetch image as blob to handle cross-origin URLs
      const response = await fetch(processedImage);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = `white-bg-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);

      toast({
        title: "下载成功",
        description: "图片已保存到本地",
      });
    } catch (error) {
      console.error("Download error:", error);
      // Fallback: open in new tab
      window.open(processedImage, '_blank');
      toast({
        title: "下载失败",
        description: "已在新窗口打开图片，请右键另存为",
        variant: "destructive",
      });
    }
  }, [processedImage, toast]);

  const handleSelectTask = useCallback(async (task: { id: number; processed_image_url: string | null; original_image_url: string | null }) => {
    const cacheKey = `task:${task.id}`;

    // Try to load from cache first
    const cachedImage = await getCachedImage(cacheKey);

    if (cachedImage) {
      setProcessedImage(cachedImage);
      setProcessedCacheKey(cacheKey);
    } else if (task.processed_image_url) {
      setProcessedImage(task.processed_image_url);
      setProcessedCacheKey(null);
    }

    if (task.original_image_url) {
      setOriginalImage(task.original_image_url);
      setOriginalCacheKey(null);
    }

    setActiveTab("generate");
  }, [getCachedImage]);

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
          <UserMenu />
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
          {user && (
            <p className="mt-3 text-sm text-muted-foreground">
              当前积分: <span className="font-semibold text-amber-500">{user.credits}</span>（每次生成消耗1积分）
            </p>
          )}
        </div>

        {/* Tabs for Generate / History */}
        <div className="max-w-4xl mx-auto">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full max-w-sm mx-auto grid-cols-2 mb-6">
              <TabsTrigger value="generate" className="flex items-center gap-2">
                <Upload className="w-4 h-4" />
                生成白底图
              </TabsTrigger>
              <TabsTrigger value="history" className="flex items-center gap-2">
                <History className="w-4 h-4" />
                历史记录
                {tasks.length > 0 && (
                  <span className="ml-1 text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                    {tasks.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="generate">
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
                    
                    {/* Options */}
                    {!processedImage && (
                      <div className="flex flex-wrap justify-center gap-6 pt-2">
                        <div className="flex flex-col gap-2">
                          <Label className="text-sm text-muted-foreground">输出分辨率</Label>
                          <Select value={resolution} onValueChange={setResolution} disabled={isProcessing}>
                            <SelectTrigger className="w-40">
                              <SelectValue placeholder="选择分辨率" />
                            </SelectTrigger>
                            <SelectContent>
                              {RESOLUTIONS.map((r) => (
                                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex flex-col gap-2">
                          <Label className="text-sm text-muted-foreground">输出比例</Label>
                          <Select value={ratio} onValueChange={setRatio} disabled={isProcessing}>
                            <SelectTrigger className="w-40">
                              <SelectValue placeholder="选择比例" />
                            </SelectTrigger>
                            <SelectContent>
                              {RATIOS.map((r) => (
                                <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    )}
                    
                    {/* Action Button */}
                    {!processedImage && (
                      <div className="flex justify-center pt-2">
                        <Button
                          onClick={handleGenerate}
                          disabled={isProcessing || (!user)}
                          size="lg"
                          className="px-8 h-12 text-base font-medium gradient-primary hover:opacity-90 transition-opacity"
                        >
                          {isProcessing ? (
                            <>处理中...</>
                          ) : !user ? (
                            <>请先登录</>
                          ) : (
                            <>
                              <Sparkles className="w-5 h-5 mr-2" />
                              生成白底图 (消耗1积分)
                            </>
                          )}
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="history">
              <div className="surface-elevated rounded-2xl shadow-medium p-6 md:p-8 border border-border/50">
                {user ? (
                  <TaskHistory 
                    tasks={tasks} 
                    onRefresh={refetchTasks} 
                    onSelect={handleSelectTask}
                  />
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>请先登录查看历史记录</p>
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={() => navigate("/auth")}
                    >
                      前往登录
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>

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
