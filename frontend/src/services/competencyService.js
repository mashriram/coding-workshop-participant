import api from './api';
const base = '/api/competencies-service';
export const competencyService = {
  list: () => api.get(base),
  get: (id) => api.get(`${base}/${id}`),
  create: (data) => api.post(base, data),
  delete: (id) => api.delete(`${base}/${id}`),
  getEmployeeCompetencies: (empId) => api.get(`${base}/employee/${empId}`),
  upsertEmployeeCompetency: (empId, data) => api.post(`${base}/employee/${empId}`, data),
};
