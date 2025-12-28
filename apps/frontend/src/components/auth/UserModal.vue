<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { isLoading, error, showAuthModal } = authStore

// Form state
const isLoginMode = ref(true)
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)

// Form validation
const emailError = ref('')
const passwordError = ref('')
const confirmPasswordError = ref('')

// Computed properties
const isFormValid = computed(() => {
  if (!email.value || !password.value) return false
  if (!isLoginMode.value && !confirmPassword.value) return false
  return true
})

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Form validation functions
const validateEmail = () => {
  if (!email.value) {
    emailError.value = 'Email is required'
    return false
  } else if (!emailPattern.test(email.value)) {
    emailError.value = 'Please enter a valid email address'
    return false
  } else {
    emailError.value = ''
    return true
  }
}

const validatePassword = () => {
  if (!password.value) {
    passwordError.value = 'Password is required'
    return false
  } else if (password.value.length < 8) {
    passwordError.value = 'Password must be at least 8 characters'
    return false
  } else {
    passwordError.value = ''
    return true
  }
}

const validateConfirmPassword = () => {
  if (!isLoginMode.value) {
    if (!confirmPassword.value) {
      confirmPasswordError.value = 'Please confirm your password'
      return false
    } else if (confirmPassword.value !== password.value) {
      confirmPasswordError.value = 'Passwords do not match'
      return false
    } else {
      confirmPasswordError.value = ''
      return true
    }
  }
  return true
}

// Form submission
const handleSubmit = async () => {
  // Clear previous errors
  authStore.clearError()

  // Validate form
  const isEmailValid = validateEmail()
  const isPasswordValid = validatePassword()
  const isConfirmPasswordValid = validateConfirmPassword()

  if (!isEmailValid || !isPasswordValid || !isConfirmPasswordValid) {
    return
  }

  // Submit form
  if (isLoginMode.value) {
    await authStore.login({
      email: email.value,
      password: password.value,
    })

    // Close modal on successful login
    if (!error.value) {
      closeModal()
    }
  } else {
    await authStore.signup({
      email: email.value,
      password: password.value,
    })

    // Close modal on successful signup/login
    if (!error.value) {
      closeModal()
    }
  }
}

// Modal control
const closeModal = () => {
  authStore.toggleAuthModal()
  resetForm()
}

const resetForm = () => {
  email.value = ''
  password.value = ''
  confirmPassword.value = ''
  emailError.value = ''
  passwordError.value = ''
  confirmPasswordError.value = ''
  authStore.clearError()
}

const switchMode = () => {
  isLoginMode.value = !isLoginMode.value
  resetForm()
}

// Watch for modal close to reset form
watch(showAuthModal, (newValue) => {
  if (!newValue) {
    resetForm()
  }
})

// Handle click outside modal
const handleBackdropClick = (event: MouseEvent) => {
  if (event.target === event.currentTarget) {
    closeModal()
  }
}
</script>

<template>
  <div
    v-if="showAuthModal"
    class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/20 backdrop-blur-sm"
    @click="handleBackdropClick"
  >
    <div
      class="relative w-full max-w-md mx-4 bg-white rounded-xl shadow-2xl border border-gray-100"
    >
      <!-- Modal Header -->
      <div class="flex items-center justify-between p-6 border-b border-gray-100">
        <h2 class="text-2xl font-bold text-gray-900">
          {{ isLoginMode ? 'Welcome Back' : 'Create Account' }}
        </h2>
        <button
          @click="closeModal"
          class="text-gray-400 hover:text-gray-600 transition-colors"
          :disabled="isLoading"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>
      </div>

      <!-- Modal Body -->
      <form @submit.prevent="handleSubmit" class="p-6 space-y-4">
        <!-- Error Alert -->
        <div
          v-if="error"
          class="p-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg"
        >
          {{ error }}
        </div>

        <!-- Email Field -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
            Email Address
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            @blur="validateEmail"
            @input="validateEmail"
            :disabled="isLoading"
            :class="[
              'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors',
              emailError ? 'border-red-500 bg-red-50' : 'border-gray-300',
            ]"
            placeholder="Enter your email"
            autocomplete="email"
          />
          <p v-if="emailError" class="mt-1 text-sm text-red-600">{{ emailError }}</p>
        </div>

        <!-- Password Field -->
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <div class="relative">
            <input
              id="password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              @blur="validatePassword"
              @input="validatePassword"
              :disabled="isLoading"
              :class="[
                'w-full px-3 py-2 pr-10 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors',
                passwordError ? 'border-red-500 bg-red-50' : 'border-gray-300',
              ]"
              placeholder="Enter your password"
              :autocomplete="isLoginMode ? 'current-password' : 'new-password'"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
              :disabled="isLoading"
            >
              <svg
                v-if="showPassword"
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                ></path>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                ></path>
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                ></path>
              </svg>
            </button>
          </div>
          <p v-if="passwordError" class="mt-1 text-sm text-red-600">{{ passwordError }}</p>
        </div>

        <!-- Confirm Password Field (Register only) -->
        <div v-if="!isLoginMode">
          <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-1">
            Confirm Password
          </label>
          <div class="relative">
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              @blur="validateConfirmPassword"
              @input="validateConfirmPassword"
              :disabled="isLoading"
              :class="[
                'w-full px-3 py-2 pr-10 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors',
                confirmPasswordError ? 'border-red-500 bg-red-50' : 'border-gray-300',
              ]"
              placeholder="Confirm your password"
              autocomplete="new-password"
            />
            <button
              type="button"
              @click="showConfirmPassword = !showConfirmPassword"
              class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
              :disabled="isLoading"
            >
              <svg
                v-if="showConfirmPassword"
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"
                ></path>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                ></path>
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                ></path>
              </svg>
            </button>
          </div>
          <p v-if="confirmPasswordError" class="mt-1 text-sm text-red-600">
            {{ confirmPasswordError }}
          </p>
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="isLoading || !isFormValid"
          class="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-all duration-200 transform hover:scale-[1.02]"
        >
          <div class="flex items-center justify-center">
            <svg
              v-if="isLoading"
              class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            {{
              isLoginMode
                ? isLoading
                  ? 'Signing In...'
                  : 'Sign In'
                : isLoading
                  ? 'Creating Account...'
                  : 'Create Account'
            }}
          </div>
        </button>
      </form>

      <!-- Modal Footer -->
      <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 rounded-b-lg">
        <p class="text-center text-sm text-gray-600">
          {{ isLoginMode ? "Don't have an account?" : 'Already have an account?' }}
          <button
            @click="switchMode"
            :disabled="isLoading"
            class="font-medium text-blue-600 hover:text-blue-800 ml-1 transition-colors"
          >
            {{ isLoginMode ? 'Sign Up' : 'Sign In' }}
          </button>
        </p>
      </div>
    </div>
  </div>
</template>
