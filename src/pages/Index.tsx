import React, { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, History, Upload } from "lucide-react";
import { ImageUploader } from "@/components/ImageUploader";
import { ImagePreview } from "@/components/ImagePreview";
import { TaskHistory } from "@/components/TaskHistory";
import { UserMenu } from "@/components/UserMenu";
import { ProcessingProgress } from "@/components/ProcessingProgress";
import { ErrorCard } from "@/components/ErrorCard";
import { EmptyState } from "@/components/EmptyState";
import { CreditsDisplay } from "@/components/CreditsDisplay";
import { TaskQueuePanel, TaskStatus } from "@/components/TaskQueuePanel";
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
import { TaskProgressData } from "@/context/WebSocketContext";
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
  // 倒计时状态
  const [countdown, setCountdown] = useState<number | null>(null);
  // 错误状态
  const [error, setError] = useState<{ type: string; message: string } | null>(null);
  // 任务队列状态
  const [taskQueue, setTaskQueue] = useState<Array<{ id: string; status: TaskStatus; name?: string; progress?: number }>>([]);
  // WebSocket 订阅清理函数
  const wsCleanupRef = useRef<(() => void) | null>(null);
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
    listenTaskStatus,
    isProcessing,
    elapsedTime,
    estimatedRemainingTime,
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

  // 同步预估剩余时间到倒计时
  useEffect(() => {
    if (isProcessing && estimatedRemainingTime !== null) {
      setCountdown(estimatedRemainingTime);
    }
  }, [isProcessing, estimatedRemainingTime]);

  const handleImageSelect = useCallback(async (imageBase64: string, cacheKey?: string) => {
    setOriginalImage(imageBase64);
    setOriginalCacheKey(cacheKey || null);
    setProcessedImage(null);
    setProcessedCacheKey(null);
    setError(null);
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!originalImage) return;

    if (!user) {
      setError({
        type: "login",
        message: "请先登录，登录后即可使用白底图生成功能",
      });
      toast({
        title: "请先登录",
        description: "登录后即可使用白底图生成功能",
        variant: "destructive",
      });
      navigate("/auth");
      return;
    }

    if (!user || user.credits < 1) {
      setError({
        type: "credits",
        message: "您的积分已用完，请充值后继续使用",
      });
      return;
    }

    setProcessedImage(null);
    setProcessedCacheKey(null);
    setError(null);

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
      const taskIdStr = String(taskId);

      // 添加到任务队列
      setTaskQueue((prev) => [
        ...prev,
        { id: taskIdStr, status: "processing" as TaskStatus, name: "生成白底图", progress: 0 },
      ]);

      // 定义任务完成回调
      const handleTaskComplete = async (data: TaskProgressData) => {
        // 更新任务队列状态
        setTaskQueue((prev) =>
          prev.map((t) =>
            t.id === taskIdStr ? { ...t, status: "completed" as TaskStatus, progress: 100 } : t
          )
        );

        // 刷新任务历史，显示新完成的任务
        await refetchTasks();

        // 从 WebSocket 数据获取结果图片
        if (data.result_image_url) {
          setProcessedImage(data.result_image_url);

          // 自动下载图片
          const link = document.createElement("a");
          link.href = data.result_image_url;
          link.download = `white-bg-${taskId}.png`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);

          toast({
            title: "生成成功",
            description: "图片已自动下载",
          });
        }
      };

      // 定义任务失败回调
      const handleTaskFailed = (error: string) => {
        console.error("任务失败:", error);
        // 更新任务队列状态
        setTaskQueue((prev) =>
          prev.map((t) => (t.id === taskIdStr ? { ...t, status: "failed" as TaskStatus } : t))
        );

        setError({
          type: "server",
          message: error,
        });
      };

      // 清理之前的 WebSocket 订阅
      wsCleanupRef.current?.();

      // 启动 WebSocket 监听任务状态
      wsCleanupRef.current = listenTaskStatus(
        taskId,
        {
          // 任务进度更新
          onUpdate: (data) => {
            // 更新任务队列进度
            setTaskQueue((prev) =>
              prev.map((t) =>
                t.id === taskIdStr
                  ? { ...t, progress: data.progress ?? t.progress }
                  : t
              )
            );
          },
          // 任务完成回调
          onComplete: handleTaskComplete,
          // 任务失败回调
          onError: handleTaskFailed,
        }
      );
    } catch (error) {
      console.error("Error generating white background:", error);
      setError({
        type: "unknown",
        message: error instanceof Error ? error.message : "生成失败，请稍后重试",
      });
      toast({
        title: "生成失败",
        description: error instanceof Error ? error.message : "请稍后重试",
        variant: "destructive",
      });
    }
  }, [originalImage, user, navigate, ratio, resolution, processImageAsync, listenTaskStatus]);

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

  // 组件卸载时清理 WebSocket 订阅
  useEffect(() => {
    return () => {
      wsCleanupRef.current?.();
    };
  }, []);

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
          {/* 积分显示卡片 */}
          {user && (
            <div className="max-w-xs mx-auto mt-4">
              <CreditsDisplay
                credits={user.credits}
                threshold={10}
                onRecharge={() => navigate("/credits")}
              />
            </div>
          )}
          {/* 显示处理耗时 */}
          {elapsedTime && (
            <p className="mt-3 text-sm text-green-500 font-medium">
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
                {/* 未上传图片时显示空状态引导 */}
                {!originalImage ? (
                  user ? (
                    // 已登录用户 - 显示上传区域
                    <ImageUploader
                      onImageSelect={handleImageSelect}
                      disabled={isProcessing}
                    />
                  ) : (
                    // 未登录用户 - 显示引导组件
                    <EmptyState
                      isLoggedIn={false}
                      onGuestAction={() => {
                        // 触发文件选择
                        const input = document.createElement("input");
                        input.type = "file";
                        input.accept = "image/*";
                        input.onchange = (e) => {
                          const file = (e.target as HTMLInputElement).files?.[0];
                          if (file) {
                            const reader = new FileReader();
                            reader.onload = (ev) => {
                              if (ev.target?.result) {
                                handleImageSelect(ev.target.result as string);
                              }
                            };
                            reader.readAsDataURL(file);
                          }
                        };
                        input.click();
                      }}
                    />
                  )
                ) : (
                  <div className="space-y-6">
                    {/* 错误状态卡片 */}
                    {error && (
                      <ErrorCard
                        type={error.type as "network" | "upload" | "server" | "credits" | "unknown"}
                        message={error.message}
                        onRetry={() => {
                          setError(null);
                          handleGenerate();
                        }}
                        onHelp={() => navigate("/help")}
                      />
                    )}

                    <ImagePreview
                      originalImage={originalImage}
                      processedImage={processedImage}
                      isProcessing={isProcessing}
                      onClear={handleClear}
                      onDownload={handleDownload}
                    />

                    {/* Options */}
                    {!processedImage && !error && (
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

                    {/* 处理进度组件 */}
                    {isProcessing && (
                      <ProcessingProgress
                        progress={countdown ? Math.max(10, 100 - countdown * 3) : 50}
                        currentStep="正在识别图片主体..."
                        estimatedRemaining={countdown}
                        onCancel={() => {
                          // 取消任务逻辑
                          toast({
                            title: "任务已取消",
                            description: "您可以重新提交任务",
                          });
                        }}
                      />
                    )}

                    {/* Action Button */}
                    {!processedImage && !error && (
                      <div className="flex justify-center pt-2">
                        <Button
                          onClick={handleGenerate}
                          disabled={isProcessing || (!user) || (user && user.credits < 1)}
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
                          ) : user.credits < 1 ? (
                            <>积分不足</>
                          ) : (
                            <>
                              <Sparkles className="w-5 h-5 mr-2" />
                              生成白底图 (消耗1积分)
                            </>
                          )}
                        </Button>
                      </div>
                    )}

                    {/* 任务队列面板 */}
                    {taskQueue.length > 0 && (
                      <div className="mt-4">
                        <TaskQueuePanel
                          tasks={taskQueue}
                          onCancelTask={(taskId) => {
                            setTaskQueue((prev) =>
                              prev.map((t) =>
                                t.id === taskId ? { ...t, status: "failed" as TaskStatus } : t
                              )
                            );
                          }}
                          onRetryTask={(taskId) => {
                            setTaskQueue((prev) =>
                              prev.map((t) =>
                                t.id === taskId ? { ...t, status: "pending" as TaskStatus, progress: 0 } : t
                              )
                            );
                          }}
                        />
                      </div>
                    )}

                    {/* Templates Info */}
                    {!isProcessing && !error && (
                      <div className="text-center text-xs text-muted-foreground mt-4">
                        <p>使用模板链: {DEFAULT_TEMPLATE_IDS.join(" -> ")}</p>
                        <p>可用模板: {templates.length} 个 | 模板链: {chains.length} 个</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="history">
              <div className="surface-elevated rounded-2xl shadow-medium p-6 md:p-8 border border-border/50">
                {user ? (
                  tasks.length > 0 ? (
                    <TaskHistory
                      tasks={tasks}
                      onRefresh={refetchTasks}
                      onSelect={handleSelectTask}
                    />
                  ) : (
                    <EmptyState isLoggedIn={true} />
                  )
                ) : (
                  <div className="text-center py-12">
                    <History className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground mb-4">请先登录查看历史记录</p>
                    <Button
                      variant="default"
                      onClick={() => navigate("/auth")}
                      className="gradient-primary hover:opacity-90 transition-opacity"
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
            Powered by Gemini 3 Pro Image - V2 异步接口
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
