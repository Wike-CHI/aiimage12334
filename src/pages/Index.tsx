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
import { supabase } from "@/integrations/supabase/client";

const RESOLUTIONS = [
  { value: "original", label: "原始尺寸" },
  { value: "1024x1024", label: "1024 × 1024" },
  { value: "1280x1280", label: "1280 × 1280" },
  { value: "2048x2048", label: "2048 × 2048" },
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
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [resolution, setResolution] = useState("original");
  const [ratio, setRatio] = useState("original");
  const [activeTab, setActiveTab] = useState("generate");
  const { toast } = useToast();
  const { user, profile, refreshProfile } = useAuth();
  const { tasks, refetch: refetchTasks } = useTaskHistory();
  const navigate = useNavigate();

  const handleImageSelect = useCallback((imageBase64: string) => {
    setOriginalImage(imageBase64);
    setProcessedImage(null);
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

    if (!profile || profile.credits < 1) {
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
      const { data, error } = await supabase.functions.invoke("generate-white-bg", {
        body: { imageBase64: originalImage, resolution, ratio },
      });

      if (error) {
        throw new Error(error.message || "处理失败");
      }

      if (data.error) {
        throw new Error(data.error);
      }

      if (data.image) {
        setProcessedImage(data.image);
        // Refresh profile to update credits display
        await refreshProfile();
        // Refresh tasks to show new history
        refetchTasks();
        toast({
          title: "生成成功",
          description: `白底图已生成，剩余积分: ${(profile?.credits ?? 1) - 1}`,
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
  }, [originalImage, toast, user, profile, refreshProfile, navigate, resolution, ratio, refetchTasks]);

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

  const handleSelectTask = useCallback((task: { processed_image_url: string | null; original_image_url: string | null }) => {
    if (task.original_image_url) {
      setOriginalImage(task.original_image_url);
    }
    if (task.processed_image_url) {
      setProcessedImage(task.processed_image_url);
    }
    setActiveTab("generate");
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
          {user && profile && (
            <p className="mt-3 text-sm text-muted-foreground">
              当前积分: <span className="font-semibold text-amber-500">{profile.credits}</span>（每次生成消耗1积分）
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
