// FastAPI 后端客户端
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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

// Generation API
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
};
