import { useState, useEffect } from 'react';
import { generationV2API } from '@/integrations/api/client';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Textarea } from '@/components/ui/textarea';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Eye, Info, Wand2 } from 'lucide-react';

export type PromptMode = 'builtin' | 'custom' | 'merge';

interface PromptSettingsProps {
  value: string;
  onChange: (value: string) => void;
  promptMode: PromptMode;
  onPromptModeChange: (mode: PromptMode) => void;
  disabled?: boolean;
}

export function PromptSettings({
  value,
  onChange,
  promptMode,
  onPromptModeChange,
  disabled
}: PromptSettingsProps) {
  const [customPrompt, setCustomPrompt] = useState(value);
  const [builtinPrompt, setBuiltinPrompt] = useState('');
  const [finalPrompt, setFinalPrompt] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const [loading, setLoading] = useState(false);

  // 同步外部 value 到内部 state
  useEffect(() => {
    setCustomPrompt(value);
  }, [value]);

  // 获取内置提示词
  useEffect(() => {
    const fetchBuiltinPrompt = async () => {
      try {
        setLoading(true);
        const res = await generationV2API.previewPrompt();
        setBuiltinPrompt(res.data.prompt);
        updateFinalPrompt(res.data.prompt, customPrompt, promptMode);
      } catch (error) {
        console.error('获取内置提示词失败:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchBuiltinPrompt();
  }, []);

  // 更新最终提示词预览
  const updateFinalPrompt = (builtin: string, custom: string, mode: PromptMode) => {
    let result = '';
    if (mode === 'builtin') {
      result = builtin;
    } else if (mode === 'custom') {
      result = custom;
    } else {
      // merge: 内置 + 自定义
      result = builtin + (custom ? '\n\n' + custom : '');
    }
    setFinalPrompt(result);
  };

  // 模式切换
  const handleModeChange = (mode: PromptMode) => {
    onPromptModeChange(mode);
    updateFinalPrompt(builtinPrompt, customPrompt, mode);
  };

  // 自定义提示词输入
  const handleCustomPromptChange = (newValue: string) => {
    setCustomPrompt(newValue);
    onChange(newValue);
    updateFinalPrompt(builtinPrompt, newValue, promptMode);
  };

  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="prompt" className="border-border/50">
        <AccordionTrigger className="text-sm font-medium hover:no-underline">
          <div className="flex items-center gap-2">
            <Wand2 className="w-4 h-4" />
            自定义提示词
            {promptMode !== 'builtin' && customPrompt && (
              <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
                已设置
              </span>
            )}
          </div>
        </AccordionTrigger>
        <AccordionContent className="pt-4 space-y-4">
          {/* 提示词模式选择 */}
          <div className="space-y-3">
            <Label className="text-xs text-muted-foreground">提示词模式</Label>
            <RadioGroup
              value={promptMode}
              onValueChange={(val) => handleModeChange(val as PromptMode)}
              disabled={disabled}
              className="flex flex-col sm:flex-row gap-3"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="builtin" id="mode-builtin" />
                <Label htmlFor="mode-builtin" className="text-sm cursor-pointer">
                  仅使用内置提示词
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="custom" id="mode-custom" />
                <Label htmlFor="mode-custom" className="text-sm cursor-pointer">
                  仅使用自定义提示词
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="merge" id="mode-merge" />
                <Label htmlFor="mode-merge" className="text-sm cursor-pointer">
                  合并使用
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* 内置提示词预览 */}
          {builtinPrompt && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs text-muted-foreground">内置提示词预览</Label>
                <Dialog open={showPreview} onOpenChange={setShowPreview}>
                  <DialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowPreview(true)}
                      disabled={disabled || loading}
                      className="h-7 text-xs"
                    >
                      <Eye className="w-3 h-3 mr-1" />
                      查看完整提示词
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
                    <DialogHeader>
                      <DialogTitle className="text-base">完整提示词预览</DialogTitle>
                    </DialogHeader>
                    <div className="whitespace-pre-wrap text-sm text-muted-foreground font-mono bg-muted p-4 rounded-lg">
                      {finalPrompt || '（无内容）'}
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
              <div className="text-xs text-muted-foreground bg-muted/50 p-3 rounded-lg line-clamp-3">
                {builtinPrompt.substring(0, 150)}...
              </div>
            </div>
          )}

          {/* 自定义提示词输入 */}
          {promptMode !== 'builtin' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="custom-prompt" className="text-sm">
                  {promptMode === 'custom' ? '自定义提示词' : '追加提示词'}
                </Label>
                <span className="text-xs text-muted-foreground">
                  ({promptMode === 'custom' ? '完全替换内置' : '追加到内置后面'})
                </span>
              </div>
              <Textarea
                id="custom-prompt"
                placeholder={
                  promptMode === 'custom'
                    ? "直接输入完整提示词..."
                    : "描述额外要求，如：保持原有色调，使背景更洁白..."
                }
                value={customPrompt}
                onChange={(e) => handleCustomPromptChange(e.target.value)}
                disabled={disabled}
                className="min-h-[80px] text-sm"
              />
            </div>
          )}

          {/* 提示信息 */}
          <div className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 p-3 rounded-lg">
            <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>
              提示词会影响 AI 处理图片的效果。内置提示词已优化为生成高质量白底图，
              如需微调效果可在此处追加额外要求。
            </p>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

// 导出类型供其他地方使用
export { type PromptMode };
