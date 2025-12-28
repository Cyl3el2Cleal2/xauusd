import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import apiClient from '@/apis/api'

interface User {
  id: string
  email: string
  is_active: boolean
  is_superuser: boolean
  is_verified: boolean
}

interface LoginCredentials {
  email: string
  password: string
}

interface SignupCredentials {
  email: string
  password: string
  money: number
  is_active?: boolean
  is_superuser?: boolean
  is_verified?: boolean
}

interface AuthResponse {
  access_token: string
  token_type: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const showAuthModal = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!user.value && !!localStorage.getItem('auth_token'))
  const currentUser = computed(() => user.value)

  // Actions
  async function toggleAuthModal() {
    showAuthModal.value = !showAuthModal.value
    return showAuthModal.value
  }
  async function login(credentials: LoginCredentials) {
    isLoading.value = true
    error.value = null

    try {
      // Create FormData for login endpoint (required by OAuth2PasswordBearer)
      const formData = new FormData()
      formData.append('username', credentials.email)
      formData.append('password', credentials.password)
      formData.append('grant_type', 'password')

      const response = await apiClient.post<AuthResponse>('/auth/jwt/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })

      if (response.data.access_token) {
        // Store token in localStorage for persistence
        localStorage.setItem('auth_token', response.data.access_token)

        // Fetch user details after successful login
        await fetchCurrentUser()

        return { success: true }
      } else {
        error.value = 'Login failed: No token received'
        return { success: false, error: error.value }
      }
    } catch (err: any) {
      console.error('Login error:', err)
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          error.value = err.response.data.detail
        } else if (err.response.data.detail.reason) {
          error.value = err.response.data.detail.reason
        } else {
          error.value = 'Login failed'
        }
      } else if (err.response?.status === 400) {
        error.value = 'Bad credentials or the user is inactive'
      } else {
        error.value = err.message || 'An unexpected error occurred during login'
      }
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function signup(credentials: SignupCredentials) {
    isLoading.value = true
    error.value = null

    try {
      const response = await apiClient.post<User>('/auth/register', credentials)

      if (response.data) {
        // After successful registration, automatically log in
        return await login({
          email: credentials.email,
          password: credentials.password,
        })
      } else {
        error.value = 'Signup failed'
        return { success: false, error: error.value }
      }
    } catch (err: any) {
      console.error('Signup error:', err)
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          error.value = err.response.data.detail
        } else if (err.response.data.detail.reason) {
          error.value = err.response.data.detail.reason
        } else {
          error.value = 'Signup failed'
        }
      } else if (err.response?.status === 400) {
        error.value = 'A user with this email already exists or password validation failed'
      } else {
        error.value = err.message || 'An unexpected error occurred during signup'
      }
      return { success: false, error: error.value }
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    isLoading.value = true
    error.value = null

    try {
      // Call logout endpoint to invalidate token on server
      await apiClient.post('/auth/jwt/logout')
    } catch (err: any) {
      console.error('Logout error:', err)
      // Continue with local logout even if server call fails
    } finally {
      // Clear local state and storage
      user.value = null
      localStorage.removeItem('auth_token')
      isLoading.value = false
    }

    return { success: true }
  }

  async function fetchCurrentUser() {
    try {
      const response = await apiClient.get<User>('/users/me')
      user.value = response.data
      return { success: true }
    } catch (err: any) {
      console.error('Fetch current user error:', err)
      if (err.response?.status === 401) {
        // Token is invalid, clear it
        localStorage.removeItem('auth_token')
        user.value = null
      }
      return { success: false, error: 'Failed to fetch user data' }
    }
  }

  // Initialize auth state from localStorage
  function initializeAuth() {
    const token = localStorage.getItem('auth_token')
    if (token && !user.value) {
      // Validate token by fetching current user
      fetchCurrentUser()
    }
  }

  // Clear any auth errors
  function clearError() {
    error.value = null
  }

  // Refresh user data
  async function refreshUser() {
    return await fetchCurrentUser()
  }

  return {
    // State
    user,
    isLoading,
    error,
    showAuthModal,

    // Getters
    isAuthenticated,
    currentUser,

    // Actions
    toggleAuthModal,
    login,
    signup,
    logout,
    fetchCurrentUser,
    initializeAuth,
    clearError,
    refreshUser,
  }
})
