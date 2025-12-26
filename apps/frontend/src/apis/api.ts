import axios from 'axios'
const baseURL = import.meta.env.VITE_API_URL || 'localhost:8000'

const apiClient = axios.create({
  baseURL: baseURL,
  headers: {
    'Content-Type': 'application/json',
    // other default headers
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized errors
    if (error.response?.status === 401) {
      // Clear invalid token
      localStorage.removeItem('auth_token')
      // You could redirect to login page here
      // window.location.href = '/login';
    }
    return Promise.reject(error)
  },
)

export default apiClient
