import { useState, useCallback, useEffect } from "react";
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
import { useImageGenerationV2 } from "@/hooks/useImageGenerationV2";
import { imageUtils } from "@/integrations/api/client";
import { GENERATION_CONFIG } from "@/config";

// 使用后端API返回的配置生成下拉选项
const RESOLUTIONS = GENERATION_CONFIG.resolutions.map(r => ({
  value: r.value,
  label: r.label
}));

const RATIOS = GENERATION_CONFIG.aspectRatios.map(r => ({
  value: r.value,
  label: r.label
}));

const DEFAULT_TEMPLATE_IDS = [
  'remove_bg',
  'standardize',
  'ecommerce',
  'color_correct'
];

const Index = () => {
  const [originalImage, setOriginalImage] = useState<string | null>(null);
  const [originalCacheKey, setOriginalCacheKey] = useState<string | null>(null);
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [processedCacheKey, setProcessedCacheKey] = useState<string | null>(null);
  // 使用后端配置的默认分辨率和比例
  const [resolution, setResolution] = useState<string>(GENERATION_CONFIG.defaultResolution);
  const [ratio, setRatio] = useState<string>(GENERATION_CONFIG.defaultAspectRatio);
  const [activeTab, setActiveTab] = useState("generate");
  const { toast } = useToast();
  const { user } = useAuth();
  const { tasks, refetch: refetchTasks } = useTaskHistory();
  const { getCachedImage } = useUploadImageCache();
  const { cacheTaskImage } = useTaskImageCache();
  const navigate = useNavigate();

  // V2 图片生成 Hook（包含同步和异步方法）
  const {
    processImage,
    processImageAsync,
    pollTaskStatus,
    isProcessing,
    elapsedTime,
    templates,
    chains,
    isLoadingTemplates,
    refreshTemplates,
  } = useImageGenerationV2({
    templateIds: DEFAULT_TEMPLATE_IDS,
  });

  // 加载模板列表
  useEffect(() => {
    refreshTemplates();
  }, [refreshTemplates]);

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

    setProcessedImage(null);
    setProcessedCacheKey(null);

    try {
      // 将 base64 转换为 File
      const response = await fetch(originalImage);
      const blob = await response.blob();
      const file = new File([blob], "image.png", { type: "image/png" });

      // V2 异步任务：立即提交，后台处理
      toast({
        title: "任务已创建",
        description: "正在后台生成白底图，可继续上传其他图片",
      });

      // 提交异步任务，获取任务ID
      const taskId = await processImageAsync(file, ratio, resolution);

      // 启动轮询任务状态
      pollTaskStatus(
        // 任务完成回调
        async (result) => {
          // 刷新任务历史，显示新完成的任务
          await refetchTasks();

          // 从刚刷新后的 tasks 中查找刚完成的任务
          const completedTask = tasks.find((t: { id: number }) => t.id === taskId);
          if (completedTask?.result_image_url) {
            setProcessedImage(completedTask.result_image_url);

            // 自动下载图片
            const link = document.createElement("a");
            link.href = completedTask.result_image_url;
            link.download = `white-bg-${taskId}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        },
        // 任务失败回调
        (error) => {
          console.error("任务失败:", error);
        }
      );
    } catch (error) {
      console.error("Error generating white background:", error);
      toast({
        title: "生成失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      });
    }
  }, [originalImage, toast, user, navigate, ratio, resolution, processImageAsync, pollTaskStatus, refetchTasks, tasks]);

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

  const handleSelectTask = useCallback(async (task: { id: number; result_image_url: string | null; original_image_url: string | null }) => {
    const cacheKey = `task:${task.id}`;

    // Try to load from cache first
    const cachedImage = await getCachedImage(cacheKey);

    if (cachedImage) {
      setProcessedImage(cachedImage);
      setProcessedCacheKey(cacheKey);
    } else if (task.result_image_url) {
      setProcessedImage(task.result_image_url);
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
          {/* 显示处理耗时 */}
          {elapsedTime && (
            <p className="mt-2 text-sm text-green-500">
              上次处理耗时: {elapsedTime.toFixed(1)} 秒
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
                                <SelectItem key={r.value} value={String(r.value)}>{r.label}</SelectItem>
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
                            <>
                              <Sparkles className="w-5 h-5 mr-2 animate-pulse" />
                              处理中...
                            </>
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

                    {/* Processing Status */}
                    {isProcessing && (
                      <div className="text-center text-sm text-muted-foreground">
                        <p>正在调用 AI 进行图像处理...</p>
                        <p className="text-xs mt-1">V2 同步接口，无需轮询，直接返回结果</p>
                      </div>
                    )}

                    {/* Templates Info */}
                    <div className="text-center text-xs text-muted-foreground mt-4">
                      <p>使用模板链: {DEFAULT_TEMPLATE_IDS.join(" -> ")}</p>
                      <p>可用模板: {templates.length} 个 | 模板链: {chains.length} 个</p>
                    </div>
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
            Powered by Gemini 3 Pro Image - V2 同步接口
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
