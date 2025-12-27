// FastAPI 后端客户端
import axios from 'axios';
import { API_CONFIG, IMAGE_CONFIG } from '@/config';

// 使用集中配置中的 API 基础 URL（必需从环境变量读取）
export const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 图片 URL 构建工具函数
export const imageUtils = {
  // 获取上传图片的完整 URL
  getUploadUrl: (path: string | null | undefined): string => {
    return IMAGE_CONFIG.getImageUrl(path);
  },
  
  // 获取结果图片的完整 URL
  getResultUrl: (path: string | null | undefined): string => {
    return IMAGE_CONFIG.getImageUrl(path);
  },
};

// 请求拦截器 - 添加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (email: string, password: string, username: string) =>
    api.post('/api/auth/register', { email, password, username }),

  login: (email: string, password: string) =>
    api.post('/api/auth/login', new URLSearchParams({
      username: email,
      password: password,
    }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),

  me: () => api.get('/api/auth/me'),

  updateProfile: (data: { username?: string; theme?: string }) =>
    api.put('/api/auth/me', data),
};

// Generation API - V1 (Deprecated, use V2 instead)
// @deprecated Use generationV2API instead for synchronous processing
export const generationAPI = {
  generate: (file: File, width: number = 1024, height: number = 1024, ratio: string = "1:1") => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('width', width.toString());
    formData.append('height', height.toString());
    formData.append('ratio', ratio);
    return api.post('/api/generate', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getTasks: (skip: number = 0, limit: number = 20) =>
    api.get('/api/tasks', { params: { skip, limit } }),

  getCredits: () => api.get('/api/credits'),

  getTaskDetail: (taskId: number) => api.get(`/api/tasks/${taskId}`),

  deleteTask: (taskId: number) => api.delete(`/api/tasks/${taskId}/delete`),

  cancelTask: (taskId: number) => api.delete(`/api/tasks/${taskId}/cancel`),

  continueTask: (taskId: number, width: number = 1024, height: number = 1024, ratio: string = "1:1") => {
    return api.post(`/api/tasks/${taskId}/continue`, null, {
      params: { width, height, ratio }
    });
  },
};

// V2 Generation API - Synchronous processing (recommended)
export const generationV2API = {
  /**
   * 上传并处理图片（同步接口，直接返回结果）
   * @param file - 图片文件
   * @param options - 处理选项
   * @returns Promise with processing result
   */
  process: (
    file: File,
    options?: {
      templateIds?: string[];
      customPrompt?: string;
      timeoutSeconds?: number;
      aspectRatio?: string;
      imageSize?: string;
    }
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    
    // 发送模板ID列表为JSON字符串
    if (options?.templateIds) {
      formData.append('template_ids', JSON.stringify(options.templateIds));
    }
    
    if (options?.customPrompt) {
      formData.append('custom_prompt', options.customPrompt);
    }
    
    if (options?.timeoutSeconds) {
      formData.append('timeout_seconds', options.timeoutSeconds.toString());
    }
    
    // 发送宽高比和分辨率
    if (options?.aspectRatio) {
      formData.append('aspect_ratio', options.aspectRatio);
    }
    
    if (options?.imageSize) {
      formData.append('image_size', options.imageSize);
    }
    
    return api.post('/api/v2/process/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * 获取生成配置
   * @returns Promise with config
   */
  getConfig: () => api.get('/api/v2/config'),

  /**
   * 预览组合后的提示词
   * @param templateIds - 模板ID列表
   * @param productCategory - 产品类目
   * @returns Promise with preview result
   */
  previewPrompt: (templateIds: string[], productCategory: string = "服装") =>
    api.post('/api/v2/preview', { template_ids: templateIds, product_category: productCategory }),

  /**
   * 获取可用的提示词模板列表
   * @returns Promise with template list
   */
  getTemplates: () => api.get('/api/v2/templates'),

  /**
   * 获取模板详情
   * @param templateId - 模板ID
   * @returns Promise with template detail
   */
  getTemplate: (templateId: string) => api.get(`/api/v2/templates/${templateId}`),

  /**
   * 获取可用的模板链列表
   * @returns Promise with chain list
   */
  getChains: () => api.get('/api/v2/chains'),

  /**
   * 获取模板分类列表
   * @returns Promise with category list
   */
  getCategories: () => api.get('/api/v2/templates/categories'),

  /**
   * 获取V2任务历史（直接从数据库查询，实时反映状态）
   * @param skip - 跳过的任务数
   * @param limit - 返回的任务数
   * @param statusFilter - 状态过滤
   * @returns Promise with task list
   */
  getTasks: (skip: number = 0, limit: number = 20, statusFilter?: string) =>
    api.get('/api/v2/tasks', { params: { skip, limit, status_filter: statusFilter } }),

  /**
   * 获取V2任务详情（直接从数据库查询）
   * @param taskId - 任务ID
   * @returns Promise with task detail
   */
  getTaskDetail: (taskId: number) => api.get(`/api/v2/tasks/${taskId}`),
};
