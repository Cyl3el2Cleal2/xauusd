import axios from 'axios';
const baseURL = import.meta.env.BASE_URL || 'localhost:'

const apiClient = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json',
    // other default headers
  },
});

// Example of adding a request interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default apiClient;
