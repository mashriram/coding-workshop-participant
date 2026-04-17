import api from './api';
const base = '/api/employees-service';
export const employeeService = {
  list: (params) => api.get(base, { params }),
  get: (id) => api.get(`${base}/${id}`),
  create: (data) => api.post(base, data),
  update: (id, data) => api.put(`${base}/${id}`, data),
  delete: (id) => api.delete(`${base}/${id}`),
};
