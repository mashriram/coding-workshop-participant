import api from './api';

const ENDPOINTS = JSON.parse(import.meta.env.VITE_API_ENDPOINTS || '{}');
const base = (ENDPOINTS['auth-service'] ? ENDPOINTS['auth-service'] : '') + '/api/auth-service';

export const authService = {
  login: (data) => api.post(`${base}/login`, data),
  register: (data) => api.post(`${base}/register`, data),
  getMe: () => api.get(`${base}/me`),
  updateMe: (data) => api.put(`${base}/me`, data),
  listUsers: () => api.get(`${base}/users`),
  updateUser: (id, data) => api.put(`${base}/users/${id}`, data),
  deleteUser: (id) => api.delete(`${base}/users/${id}`),

  // Local helpers
  saveSession: (token, user) => {
    localStorage.setItem('acme_token', token);
    localStorage.setItem('acme_user', JSON.stringify(user));
  },
  clearSession: () => {
    localStorage.removeItem('acme_token');
    localStorage.removeItem('acme_user');
  },
  getUser: () => {
    try { return JSON.parse(localStorage.getItem('acme_user')); }
    catch { return null; }
  },
  isAuthenticated: () => !!localStorage.getItem('acme_token'),
};
