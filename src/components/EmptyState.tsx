import React from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  ArrowRight,
  Image as ImageIcon,
  Zap,
  CreditCard,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  isLoggedIn?: boolean;
  onGuestAction?: () => void;
}

export function EmptyState({
  isLoggedIn = false,
  onGuestAction,
}: EmptyStateProps) {
  const navigate = useNavigate();

  const handleLogin = () => {
    navigate("/auth");
  };

  const handleGuest = () => {
    if (onGuestAction) {
      onGuestAction();
    }
  };

  return (
    <div className="flex flex-col items-center gap-8 py-8 animate-fade-in">
      {/* 主图标 */}
      <div className="relative">
        <div className="p-6 rounded-3xl bg-gradient-to-br from-primary/10 to-purple-500/10 border border-primary/20">
          <Sparkles className="w-16 h-16 text-primary" />
        </div>
        <div className="absolute -bottom-2 -right-2 p-2 rounded-xl bg-amber-100 dark:bg-amber-900/30">
          <Zap className="w-5 h-5 text-amber-500" />
        </div>
      </div>

      {/* 标题 */}
      <div className="text-center">
        <h2 className="text-2xl font-display font-bold text-foreground mb-2">
          {isLoggedIn ? "开始生成白底图" : "欢迎使用白底图生成器"}
        </h2>
        <p className="text-muted-foreground max-w-sm">
          {isLoggedIn
            ? "上传您的图片，AI 将自动识别主体并生成纯白背景"
            : "上传任意图片，AI 智能识别主体，自动生成纯白背景图片"}
        </p>
      </div>

      {/* 功能特点 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-lg">
        {[
          {
            icon: <ImageIcon className="w-5 h-5" />,
            title: "智能抠图",
            desc: "AI 精准识别",
          },
          {
            icon: <Zap className="w-5 h-5" />,
            title: "快速处理",
            desc: "几秒完成",
          },
          {
            icon: <CreditCard className="w-5 h-5" />,
            title: "高清输出",
            desc: "保持清晰度",
          },
        ].map((feature, i) => (
          <div
            key={i}
            className="flex flex-col items-center gap-2 p-4 rounded-xl bg-card border border-border/50 hover:border-primary/30 transition-all duration-200"
          >
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              {feature.icon}
            </div>
            <h3 className="font-medium text-foreground text-sm">
              {feature.title}
            </h3>
            <p className="text-xs text-muted-foreground">{feature.desc}</p>
          </div>
        ))}
      </div>

      {/* 操作按钮 */}
      <div className="flex flex-col sm:flex-row gap-3 mt-4">
        {isLoggedIn ? (
          <Button
            size="lg"
            onClick={handleGuest}
            className="gap-2 gradient-primary hover:opacity-90 transition-opacity"
          >
            <ImageIcon className="w-5 h-5" />
            上传图片开始处理
          </Button>
        ) : (
          <>
            <Button
              size="lg"
              onClick={handleLogin}
              className="gap-2 gradient-primary hover:opacity-90 transition-opacity"
            >
              <Sparkles className="w-5 h-5" />
              立即登录
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={handleGuest}
              className="gap-2"
            >
              游客体验
              <ArrowRight className="w-4 h-4" />
            </Button>
          </>
        )}
      </div>

      {/* 提示信息 */}
      {!isLoggedIn && (
        <p className="text-xs text-muted-foreground text-center">
          登录后可保存历史记录，享受更多功能
        </p>
      )}
    </div>
  );
}
