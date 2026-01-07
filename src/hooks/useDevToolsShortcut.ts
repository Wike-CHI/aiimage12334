import { useEffect } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';

export function useDevToolsShortcut() {
  useEffect(() => {
    const handleKeyDown = async (event: KeyboardEvent) => {
      if (event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key === 'I')) {
        event.preventDefault();
        try {
          const window = getCurrentWindow();
          // @ts-expect-error - toggleDevTools 在类型定义中可能缺失但运行时存在
          if (typeof window.toggleDevTools === 'function') {
            // @ts-expect-error toggleDevTools 方法在类型定义中可能缺失
            await window.toggleDevTools();
          }
        } catch (e) {
          // 非 Tauri 环境，静默失败
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}
