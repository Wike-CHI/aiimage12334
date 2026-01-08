import { useEffect } from 'react';

// 动态导入 Tauri API，避免非 Tauri 环境报错
let invoke: any;
try {
  const tauriCore = require('@tauri-apps/api/core');
  invoke = tauriCore.invoke;
} catch (e) {
  // 非 Tauri 环境，invoke 为 undefined
  invoke = undefined;
}

export function useDevToolsShortcut() {
  useEffect(() => {
    // 只有在 Tauri 环境中才注册快捷键
    if (!invoke) return;

    const handleKeyDown = async (event: KeyboardEvent) => {
      if (event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key === 'I')) {
        event.preventDefault();
        try {
          await invoke('open_devtools');
        } catch (e) {
          // 静默失败
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}
