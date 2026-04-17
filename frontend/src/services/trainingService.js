import api from './api';
const base = '/api/training-service';
export const trainingService = {
  list: (params) => api.get(base, { params }),
  get: (id) => api.get(`${base}/${id}`),
  create: (data) => api.post(base, data),
  update: (id, data) => api.put(`${base}/${id}`, data),
  delete: (id) => api.delete(`${base}/${id}`),
};
