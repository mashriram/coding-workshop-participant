import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: `${API_URL}/api` });

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('acme_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 globally — redirect to login
api.interceptors.response.use(
  (res) => {
    // Handle LocalStack returning 200 OK for error bodies
    if (res.data && res.data.error) {
      if (res.data.error === "Invalid email or password" || res.data.error.includes("Authentication required") || res.data.error.includes("expired")) {
        localStorage.removeItem('acme_token');
        localStorage.removeItem('acme_user');
        window.location.href = '/login';
        return Promise.reject({ response: { status: 401, data: res.data } });
      }
      return Promise.reject({ response: { status: 400, data: res.data } });
    }
    return res;
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('acme_token');
      localStorage.removeItem('acme_user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
