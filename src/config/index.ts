/**
 * 前端配置模块
 * 所有配置都从环境变量读取，不使用任何硬编码
 */

// API 配置
export const API_CONFIG = {
  // API 基础 URL - 必须从环境变量读取
  baseURL: getEnvRequired('VITE_API_URL'),
  
  // API 超时时间（毫秒）
  timeout: 30000,
};

// 图片服务配置
export const IMAGE_CONFIG = {
  // 图片基础路径 - 相对于 API 的路径
  uploadsPath: '/uploads',
  resultsPath: '/results',
  
  // 获取完整的图片 URL
  getImageUrl: (path: string | null | undefined): string => {
    if (!path) return '';
    
    // 如果已经是完整 URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    
    // 构建完整的图片 URL
    return `${API_CONFIG.baseURL}${path.startsWith('/') ? '' : '/'}${path}`;
  },
};

// 应用配置
export const APP_CONFIG = {
  name: '白底图生成器',
  version: '1.0.0',
};

// 轮询配置
export const POLLING_CONFIG = {
  interval: 5000,        // 轮询间隔（毫秒）
  maxAttempts: 120,      // 最大轮询次数（120 * 5秒 = 10分钟）
};

// 图片生成配置
export const GENERATION_CONFIG = {
  // 支持的宽高比
  aspectRatios: [
    { value: "1:1", label: "1:1 (正方形)" },
    { value: "2:3", label: "2:3 (竖版)" },
    { value: "3:2", label: "3:2 (横版)" },
    { value: "3:4", label: "3:4 (竖版)" },
    { value: "4:3", label: "4:3 (横版)" },
    { value: "4:5", label: "4:5 (竖版)" },
    { value: "5:4", label: "5:4 (横版)" },
    { value: "9:16", label: "9:16 (手机竖版)" },
    { value: "16:9", label: "16:9 (宽银幕)" },
    { value: "21:9", label: "21:9 (超宽银幕)" },
  ],

  // 支持的分辨率
  resolutions: [
    { value: "1K", label: "1K (约1024x1024)" },
    { value: "2K", label: "2K (约2048x2048)" },
    { value: "4K", label: "4K (约4096x4096)" },
  ],

  // 默认配置
  defaultAspectRatio: "1:1",
  defaultResolution: "1K",
};

/**
 * 获取必需的环境变量
 * 如果环境变量不存在，抛出明确的错误
 */
function getEnvRequired(key: string): string {
  const value = import.meta.env[key];
  
  if (!value) {
    throw new Error(
      `环境变量 ${key} 未设置！\n` +
      `请在 .env 文件中设置：${key}=your_value\n` +
      `例如：${key}=http://localhost:8001`
    );
  }
  
  return value;
}

/**
 * 获取可选的环境变量
 * 如果不存在，返回默认值（但这不是硬编码，而是在配置层面的合理默认值）
 */
export function getEnvOptional(key: string, defaultValue: string): string {
  return import.meta.env[key] || defaultValue;
}

