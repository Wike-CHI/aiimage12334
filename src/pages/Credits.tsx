import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  CreditCard,
  Wallet,
  CheckCircle2,
  Gift,
  ArrowLeft,
  Zap,
  Shield,
  Clock,
  Coins,
  Flame,
  Building2,
  MessageCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserMenu } from "@/components/UserMenu";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";

// 定价配置
const PRICING_CONFIG = {
  "1K": { price: 0.94, credits: 1 },
  "2K": { price: 0.94, credits: 1 },
  "4K": { price: 1.68, credits: 2 },
};

// 套餐配置
const CREDIT_PACKAGES = [
  {
    id: "basic",
    name: "基础套餐",
    credits: 50,
    originalPrice: 47,
    price: 39,
    bonus: 0,
    isRecommended: false,
    icon: Coins,
  },
  {
    id: "standard",
    name: "标准套餐",
    credits: 100,
    originalPrice: 94,
    price: 79,
    bonus: 10,
    isRecommended: true,
    icon: Sparkles,
  },
  {
    id: "value",
    name: "超值套餐",
    credits: 200,
    originalPrice: 188,
    price: 149,
    bonus: 30,
    isRecommended: false,
    icon: Flame,
  },
  {
    id: "enterprise",
    name: "企业套餐",
    credits: 500,
    originalPrice: 470,
    price: 349,
    bonus: 100,
    isRecommended: false,
    icon: Building2,
  },
];

// 支付方式
const PAYMENT_METHODS = [
  { id: "wechat", name: "微信支付", icon: MessageCircle },
  { id: "alipay", name: "支付宝", icon: CreditCard },
];

const Credits = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  const [selectedPackage, setSelectedPackage] = useState<string | null>("standard");
  const [selectedPayment, setSelectedPayment] = useState<string>("wechat");
  const [isProcessing, setIsProcessing] = useState(false);

  const handlePurchase = async () => {
    if (!selectedPackage) {
      toast({
        title: "请选择套餐",
        description: "请先选择一个充值套餐",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);

    // 模拟支付流程
    await new Promise((resolve) => setTimeout(resolve, 2000));

    toast({
      title: "充值成功",
      description: "积分已到账，请尽情使用吧！",
    });

    setIsProcessing(false);
    setSelectedPackage(null);
  };

  const selectedPackageData = CREDIT_PACKAGES.find((p) => p.id === selectedPackage);

  return (
    <div className="min-h-screen gradient-subtle">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="container max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/")}
              className="gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              返回
            </Button>
            <div className="h-6 w-px bg-border" />
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl gradient-primary">
                <Sparkles className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-display font-semibold text-lg">积分充值</span>
            </div>
          </div>
          <UserMenu />
        </div>
      </header>

      {/* Main Content */}
      <main className="container max-w-5xl mx-auto px-4 py-8 md:py-12">
        {/* 当前积分余额 */}
        <div className="max-w-2xl mx-auto mb-10">
          <div className="surface-elevated rounded-2xl shadow-medium p-6 md:p-8 border border-border/50">
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-100 to-yellow-100 dark:from-amber-900/30 dark:to-yellow-900/30">
                <Wallet className="w-10 h-10 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="flex-1 text-center md:text-left">
                <p className="text-sm text-muted-foreground mb-1">当前积分余额</p>
                <p className="text-4xl font-bold text-amber-600 dark:text-amber-400 mb-2">
                  {user?.credits || 0}
                  <span className="text-lg font-normal text-muted-foreground ml-2">
                    积分
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">
                  约可生成{" "}
                  <span className="font-medium text-foreground">
                    {Math.floor((user?.credits || 0) / 1)}
                  </span>{" "}
                  张 1K/2K 图片，或{" "}
                  <span className="font-medium text-foreground">
                    {Math.floor((user?.credits || 0) / 2)}
                  </span>{" "}
                  张 4K 图片
                </p>
              </div>
              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate("/")}
                className="hidden md:flex"
              >
                快速使用
              </Button>
            </div>
          </div>
        </div>

        {/* 选择充值套餐 */}
        <div className="max-w-4xl mx-auto mb-10">
          <h2 className="text-2xl font-display font-bold text-center mb-2">
            选择充值套餐
          </h2>
          <p className="text-muted-foreground text-center mb-8">
            充值积分可用于生成白底图，支持多种分辨率
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {CREDIT_PACKAGES.map((pkg) => (
              <div
                key={pkg.id}
                onClick={() => setSelectedPackage(pkg.id)}
                className={`
                  relative p-5 rounded-2xl border-2 cursor-pointer transition-all duration-300
                  ${
                    selectedPackage === pkg.id
                      ? "border-primary bg-primary/5 shadow-medium scale-105"
                      : "border-border bg-card hover:border-primary/30 hover:shadow-soft"
                  }
                `}
              >
                {/* 推荐标记 */}
                {pkg.isRecommended && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-primary to-purple-500 text-white text-xs font-medium">
                    推荐
                  </div>
                )}

                {/* 图标 */}
                <div className="flex justify-center mb-3">
                  <pkg.icon className="w-10 h-10 text-primary" />
                </div>

                {/* 套餐名称 */}
                <h3 className="text-center font-semibold text-foreground mb-1">
                  {pkg.name}
                </h3>

                {/* 积分数量 */}
                <div className="text-center mb-3">
                  <span className="text-3xl font-bold text-primary">
                    {pkg.credits + pkg.bonus}
                  </span>
                  <span className="text-sm text-muted-foreground ml-1">
                    积分
                  </span>
                  {pkg.bonus > 0 && (
                    <span className="block text-xs text-green-500 mt-1">
                      赠送 {pkg.bonus} 积分
                    </span>
                  )}
                </div>

                {/* 价格 */}
                <div className="text-center">
                  <span className="text-lg font-bold text-foreground">
                    ¥{pkg.price}
                  </span>
                  {pkg.originalPrice > pkg.price && (
                    <span className="text-sm text-muted-foreground line-through ml-2">
                      ¥{pkg.originalPrice}
                    </span>
                  )}
                </div>

                {/* 选中状态 */}
                {selectedPackage === pkg.id && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle2 className="w-5 h-5 text-primary" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 支付方式 */}
        <div className="max-w-2xl mx-auto mb-10">
          <h3 className="text-lg font-semibold text-center mb-4">选择支付方式</h3>
          <div className="flex gap-4 justify-center">
            {PAYMENT_METHODS.map((method) => (
              <button
                key={method.id}
                onClick={() => setSelectedPayment(method.id)}
                className={`
                  flex items-center gap-3 px-6 py-4 rounded-xl border-2 transition-all duration-200
                  ${
                    selectedPayment === method.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30"
                  }
                `}
              >
                <method.icon className="w-6 h-6" />
                <span className="font-medium">{method.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* 立即充值按钮 */}
        <div className="max-w-md mx-auto mb-12">
          <Button
            onClick={handlePurchase}
            disabled={!selectedPackage || isProcessing}
            size="lg"
            className="w-full h-14 text-lg font-medium gradient-primary hover:opacity-90 transition-opacity"
          >
            {isProcessing ? (
              <>
                <Sparkles className="w-5 h-5 mr-2 animate-pulse" />
                支付中...
              </>
            ) : (
              <>
                <CreditCard className="w-5 h-5 mr-2" />
                立即充值 ¥{selectedPackageData?.price || 0}
              </>
            )}
          </Button>
        </div>

        {/* 价格说明 */}
        <div className="max-w-3xl mx-auto">
          <div className="surface-elevated rounded-2xl shadow-soft p-6 border border-border/50">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              价格说明
            </h3>
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  分辨率定价
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span>1K / 2K 分辨率</span>
                    </div>
                    <span className="font-medium">1 积分/张</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span>4K 分辨率</span>
                    </div>
                    <span className="font-medium">2 积分/张</span>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3">
                  API 成本
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-green-500" />
                      <span>1K / 2K</span>
                    </div>
                    <span className="text-sm">¥0.94/张</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-blue-500" />
                      <span>4K</span>
                    </div>
                    <span className="text-sm">¥1.68/张</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-4 p-4 rounded-lg bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 text-sm">
              <p className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                基于 Gemini 3 Pro Image API 成本定价，套餐充值更优惠
              </p>
            </div>
          </div>
        </div>

        {/* 促销信息 */}
        <div className="max-w-3xl mx-auto mt-6">
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Gift className="w-4 h-4 text-green-500" />
            <span>充值越多，赠送越多，批量处理更划算</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-auto">
        <div className="container max-w-5xl mx-auto px-4 py-6 text-center">
          <p className="text-sm text-muted-foreground">
            积分有效期：永久有效 · 最终解释权归平台所有
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Credits;
