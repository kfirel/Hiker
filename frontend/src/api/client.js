import axios from 'axios';

// Get admin token from localStorage
const getToken = () => localStorage.getItem('admin_token');

// Create axios instance
const apiClient = axios.create({
  baseURL: '/a', // Admin API prefix
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to all requests
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers['X-Admin-Token'] = token;
  }
  return config;
});

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token invalid or missing
      localStorage.removeItem('admin_token');
      window.location.href = '/admin/login';
    }
    return Promise.reject(error);
  }
);

// API functions
export const statsAPI = {
  getOverview: () => apiClient.get('/stats/overview'),
  getTrends: (days = 30) => apiClient.get(`/stats/trends?days=${days}`),
  getPeakHours: () => apiClient.get('/stats/peak-hours'),
};

export const logsAPI = {
  getErrors: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient.get(`/logs/errors?${query}`);
  },
  getActivity: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient.get(`/logs/activity?${query}`);
  },
  cleanup: (days = 90) => apiClient.delete(`/logs/cleanup?days=${days}`),
};

export const usersAPI = {
  list: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient.get(`/users?${query}`);
  },
  getDetails: (phoneNumber) => apiClient.get(`/users/${phoneNumber}/details`),
  getHistory: (phoneNumber, limit = 50) => 
    apiClient.get(`/users/${phoneNumber}/history?limit=${limit}`),
  exportCSV: () => {
    return apiClient.get('/users/export/csv', { responseType: 'blob' });
  },
  delete: (phoneNumber) => apiClient.delete(`/users/${phoneNumber}`),
};

export const ridesAPI = {
  getActive: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return apiClient.get(`/rides/active?${query}`);
  },
  delete: (phoneNumber, rideId, rideType) => 
    apiClient.delete(`/rides/${phoneNumber}/${rideId}?ride_type=${rideType}`),
  exportCSV: (rideType = null) => {
    const query = rideType ? `?ride_type=${rideType}` : '';
    return apiClient.get(`/rides/export/csv${query}`, { responseType: 'blob' });
  },
  calculateRoutes: () => 
    apiClient.post('/rides/calculate-routes'),
};

export default apiClient;

