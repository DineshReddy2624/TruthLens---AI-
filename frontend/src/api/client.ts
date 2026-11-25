import axios from 'axios';

const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor: handle 401 and auto-refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token: newRefresh } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefresh);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  },
);

// Auth API
export const authAPI = {
  register: (data: { name: string; email: string; password: string }) =>
    apiClient.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    apiClient.post('/auth/login', data),
  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  me: () => apiClient.get('/auth/me'),
};

// Verification API
export const verifyAPI = {
  submitText: (data: { text: string; input_type?: string }) =>
    apiClient.post('/verify/submit-text', data),
  submitUrl: (data: { url: string }) =>
    apiClient.post('/verify/submit-url', data),
  submitFile: (formData: FormData) =>
    apiClient.post('/verify/submit-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getVerification: (id: number) =>
    apiClient.get(`/verify/${id}`),
  listVerifications: () =>
    apiClient.get('/verify'),
  getDashboardStats: () =>
    apiClient.get('/verify/stats/dashboard'),
};

// RAG API
export const ragAPI = {
  chat: (requestId: number, message: string) =>
    apiClient.post('/rag/chat', { request_id: requestId, message }),
  getHistory: (requestId: number) =>
    apiClient.get(`/rag/history/${requestId}`),
};

// History API
export const historyAPI = {
  list: (params?: { q?: string; label?: string; input_type?: string; limit?: number; offset?: number }) =>
    apiClient.get('/history', { params }),
};

// Reports API
export const reportsAPI = {
  generate: (requestId: number) =>
    apiClient.post(`/reports/generate/${requestId}`),
  download: (requestId: number) =>
    apiClient.get(`/reports/download/${requestId}`, { responseType: 'blob' }),
  downloadUrl: (requestId: number) => {
    const token = localStorage.getItem('access_token');
    return `/api/v1/reports/download/${requestId}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
  },
};

// Admin API
export const adminAPI = {
  getUsers: () => apiClient.get('/admin/users'),
  toggleUser: (userId: number) => apiClient.post(`/admin/users/${userId}/toggle-status`),
  getTrusted: () => apiClient.get('/admin/trusted-sources'),
  addTrusted: (data: { domain: string; category?: string; notes?: string }) =>
    apiClient.post('/admin/trusted-sources', data),
  deleteTrusted: (sourceId: number) =>
    apiClient.delete(`/admin/trusted-sources/${sourceId}`),
  getLogs: (params?: { agent_name?: string; request_id?: number; errors_only?: boolean; limit?: number }) =>
    apiClient.get('/admin/logs', { params }),
  getStats: () => apiClient.get('/admin/stats'),
};

export default apiClient;
