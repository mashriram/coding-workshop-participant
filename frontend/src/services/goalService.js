import api from './api';
const base = '/api/goals-service';
export const goalService = {
  list: (params) => api.get(base, { params }),
  get: (id) => api.get(`${base}/${id}`),
  create: (data) => api.post(base, data),
  update: (id, data) => api.put(`${base}/${id}`, data),
  updateProgress: (id, progress) => api.put(`${base}/${id}/progress`, { progress }),
  delete: (id) => api.delete(`${base}/${id}`),
};
