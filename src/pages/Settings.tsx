import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Palette, User, Moon, Sun, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/hooks/useAuth';

const Settings = () => {
  const { user, updateProfile } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [username, setUsername] = useState('');
  const [theme, setTheme] = useState<'light' | 'dark' | 'auto'>('auto');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setUsername(user.username);
      setTheme(user.theme as 'light' | 'dark' | 'auto');
    }
  }, [user]);

  const handleSaveProfile = async () => {
    if (!username.trim()) {
      toast({
        title: '失败',
        description: '用户名不能为空',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const { error } = await updateProfile({ username });
      if (error) throw error;
      toast({ title: '成功', description: '用户名已更新' });
    } catch (error) {
      toast({
        title: '失败',
        description: error instanceof Error ? error.message : '用户名更新失败',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleThemeChange = async (newTheme: 'light' | 'dark' | 'auto') => {
    setTheme(newTheme);
    const { error } = await updateProfile({ theme: newTheme });
    if (!error) {
      applyTheme(newTheme);
      toast({ title: '成功', description: '主题已更新' });
    }
  };

  const applyTheme = (theme: string) => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    if (theme === 'auto') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  };

  // Apply theme on mount
  useEffect(() => {
    if (user) {
      applyTheme(user.theme);
    }
  }, [user]);

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen gradient-subtle">
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm">
        <div className="container max-w-5xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm">返回首页</span>
          </button>
          <h1 className="font-display font-semibold text-lg">个人设置</h1>
        </div>
      </header>

      <main className="container max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* 用户信息卡片 */}
        <div className="surface-elevated rounded-xl p-6 border border-border/50">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-primary" />
            <h2 className="font-semibold">基本信息</h2>
          </div>

          <div className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="输入用户名"
              />
            </div>

            <div className="grid gap-2">
              <Label>用户编号</Label>
              <div className="px-3 py-2 rounded-md bg-muted text-muted-foreground text-sm flex items-center gap-2">
                <Badge variant="secondary">{user.user_code || '暂无'}</Badge>
              </div>
            </div>

            <div className="grid gap-2">
              <Label>邮箱</Label>
              <div className="px-3 py-2 rounded-md bg-muted text-muted-foreground text-sm">
                {user.email}
              </div>
            </div>

            <div className="grid gap-2">
              <Label>注册时间</Label>
              <div className="px-3 py-2 rounded-md bg-muted text-muted-foreground text-sm">
                {new Date(user.created_at).toLocaleString('zh-CN')}
              </div>
            </div>

            <Button
              onClick={handleSaveProfile}
              disabled={loading || !username.trim()}
              className="mt-4"
            >
              {loading ? '保存中...' : '保存修改'}
            </Button>
          </div>
        </div>

        {/* 主题设置卡片 */}
        <div className="surface-elevated rounded-xl p-6 border border-border/50">
          <div className="flex items-center gap-3 mb-6">
            <Palette className="w-5 h-5 text-primary" />
            <h2 className="font-semibold">外观主题</h2>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <button
              type="button"
              onClick={() => handleThemeChange('light')}
              className={`p-4 rounded-lg border-2 transition-all ${
                theme === 'light' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
              }`}
            >
              <Sun className="w-6 h-6 mx-auto mb-2" />
              <p className="text-sm font-medium">浅色</p>
            </button>

            <button
              type="button"
              onClick={() => handleThemeChange('dark')}
              className={`p-4 rounded-lg border-2 transition-all ${
                theme === 'dark' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
              }`}
            >
              <Moon className="w-6 h-6 mx-auto mb-2" />
              <p className="text-sm font-medium">深色</p>
            </button>

            <button
              type="button"
              onClick={() => handleThemeChange('auto')}
              className={`p-4 rounded-lg border-2 transition-all ${
                theme === 'auto' ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
              }`}
            >
              <Monitor className="w-6 h-6 mx-auto mb-2" />
              <p className="text-sm font-medium">跟随系统</p>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Settings;
