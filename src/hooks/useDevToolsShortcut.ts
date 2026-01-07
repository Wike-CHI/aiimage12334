import { useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

export function useDevToolsShortcut() {
  useEffect(() => {
    const handleKeyDown = async (event: KeyboardEvent) => {
      if (event.key === 'F12' || (event.ctrlKey && event.shiftKey && event.key === 'I')) {
        event.preventDefault();
        try {
          await invoke('open_devtools');
        } catch (e) {
          // 非 Tauri 环境，静默失败
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
}
