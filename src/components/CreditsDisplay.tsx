import React from "react";
import { Sparkles, AlertCircle, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CreditsDisplayProps {
  credits: number;
  threshold?: number;
  onRecharge?: () => void;
  onViewHistory?: () => void;
}

export function CreditsDisplay({
  credits,
  threshold = 10,
  onRecharge,
  onViewHistory,
}: CreditsDisplayProps) {
  const isLow = credits <= threshold;
  const maxCredits = Math.max(credits, 100); // 用于计算进度条宽度

  return (
    <div
      className={`
        relative overflow-hidden rounded-2xl border transition-all duration-300
        ${
          isLow
            ? "bg-gradient-to-r from-red-50 to-orange-50 border-red-200 dark:from-red-950/20 dark:to-orange-950/20 dark:border-red-800/50"
            : "bg-gradient-to-r from-amber-50 to-yellow-50 border-amber-200 dark:from-amber-950/20 dark:to-yellow-950/20 dark:border-amber-800/50"
        }
      `}
    >
      {/* 背景装饰 */}
      <div className="absolute top-0 right-0 w-32 h-32 transform translate-x-8 -translate-y-8">
        <div
          className={`w-24 h-24 rounded-full opacity-10 ${
            isLow ? "bg-red-500" : "bg-amber-500"
          }`}
        />
      </div>

      <div className="relative p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl ${
                isLow
                  ? "bg-red-100 dark:bg-red-900/30 text-red-500"
                  : "bg-amber-100 dark:bg-amber-900/30 text-amber-500"
              }`}
            >
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium">当前积分</p>
              <p
                className={`text-2xl font-bold ${
                  isLow ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"
                }`}
              >
                {credits}
              </p>
            </div>
          </div>

          {/* 低积分警告 */}
          {isLow && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs font-medium animate-pulse">
              <AlertCircle className="w-3.5 h-3.5" />
              积分不足
            </div>
          )}
        </div>

        {/* 进度条 */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
            <span>已用积分</span>
            <span>剩余 {Math.round((credits / maxCredits) * 100)}%</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isLow
                  ? "bg-gradient-to-r from-red-400 to-red-500"
                  : "bg-gradient-to-r from-amber-400 to-yellow-500"
              }`}
              style={{
                width: `${Math.min((credits / maxCredits) * 100, 100)}%`,
              }}
            />
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-2">
          {onRecharge && (
            <Button
              size="sm"
              onClick={onRecharge}
              className={`flex-1 ${
                isLow
                  ? "bg-red-500 hover:bg-red-600 text-white"
                  : "bg-amber-500 hover:bg-amber-600 text-white"
              } transition-all duration-200`}
            >
              立即充值
            </Button>
          )}
          {onViewHistory && (
            <Button
              variant="outline"
              size="sm"
              onClick={onViewHistory}
              className="flex items-center gap-1"
            >
              消费记录
              <ChevronRight className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>

        {/* 提示 */}
        <p className="text-xs text-muted-foreground mt-3 text-center">
          每次生成白底图消耗 1 积分
        </p>
      </div>
    </div>
  );
}
