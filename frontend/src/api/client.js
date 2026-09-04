import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Watchlist API
export const watchlistAPI = {
  getAll: () => api.get('/watchlist'),
  add: (symbol, exchange) => api.post('/watchlist', { symbol, exchange }),
  remove: (id) => api.delete(`/watchlist/${id}`),
  check: (symbol) => api.get(`/watchlist/${symbol}/exists`),
};

// Alerts API
export const alertsAPI = {
  getAll: () => api.get('/alerts'),
  getForSymbol: (symbol) => api.get(`/alerts/symbol/${symbol}`),
  create: (data) => api.post('/alerts', data),
  update: (id, data) => api.put(`/alerts/${id}`, data),
  delete: (id) => api.delete(`/alerts/${id}`),
  getLogs: (alertId) => api.get(`/alerts/${alertId}/logs`),
};

// Prices API
export const pricesAPI = {
  getCurrent: (symbol) => api.get(`/prices/${symbol}`),
  getHistory: (symbol, days = 30) => api.get(`/prices/${symbol}/history?days=${days}`),
  refresh: (symbol) => api.post(`/prices/refresh/${symbol}`),
};

// Analysis API
export const analysisAPI = {
  getLatest: (symbol) => api.get(`/analysis/${symbol}`),
  refresh: (symbol) => api.post(`/analysis/${symbol}/refresh`),
  getHistory: (symbol, limit = 10) => api.get(`/analysis/${symbol}/history?limit=${limit}`),
  getFeedback: (analysisId) => api.get(`/analysis/feedback/${analysisId}`),
};

// Risk Profile API
export const riskProfileAPI = {
  get: () => api.get('/risk-profile'),
  create: (data) => api.post('/risk-profile', data),
  update: (data) => api.put('/risk-profile', data),
};

export default api;
