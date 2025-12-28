<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Modal state
const showLogin = ref(true)

// Form state
const email = ref('')
const password = ref('')
const money = ref(1000)
const rememberMe = ref(false)
const isSubmitting = ref(false)

// Computed properties
const isFormValid = computed(() => {
  return email.value.trim() !== '' && password.value.length >= 3
})

const buttonDisabled = computed(() => {
  return !isFormValid.value || isSubmitting.value || authStore.isLoading
})

// Methods
const openModal = () => {
  authStore.showAuthModal = true
  resetForm()
  authStore.clearError()
}

const closeModal = () => {
  authStore.showAuthModal = false
  resetForm()
  authStore.clearError()
}

const resetForm = () => {
  email.value = ''
  password.value = ''
  rememberMe.value = false
  isSubmitting.value = false
}

const toggleForm = () => {
  showLogin.value = !showLogin.value
  resetForm()
  authStore.clearError()
}

const handleSubmit = async (e: Event) => {
  e.preventDefault()

  if (!isFormValid.value) return

  isSubmitting.value = true

  try {
    if (showLogin.value) {
      // Login
      const result = await authStore.login({
        email: email.value.trim(),
        password: password.value,
      })

      if (result.success) {
        closeModal()
        // You could add a success notification here
        console.log('Login successful!')
      }
    } else {
      // Signup
      const result = await authStore.signup({
        email: email.value.trim(),
        password: password.value,
        money: money.value,
      })

      if (result.success) {
        closeModal()
        // You could add a success notification here
        console.log('Signup successful!')
      }
    }
  } catch (error) {
    console.error('Authentication error:', error)
  } finally {
    isSubmitting.value = false
  }
}

const handleLogout = async () => {
  const result = await authStore.logout()
  if (result.success) {
    console.log('Logout successful!')
  }
}

// Initialize auth on component mount
authStore.initializeAuth()
</script>

<template>
  <!-- Auth Button -->
  <button
    v-if="!authStore.isAuthenticated"
    @click="openModal"
    class="text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none"
    type="button"
  >
    {{ showLogin ? 'Sign In' : 'Sign Up' }}
  </button>

  <!-- User Menu (when authenticated) -->
  <div v-else class="relative">
    <button
      @click="openModal"
      class="text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none flex items-center gap-2"
      type="button"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
        />
      </svg>
      <span>{{ authStore.currentUser?.email }}</span>
    </button>
  </div>

  <!-- Main modal -->
  <div
    v-show="authStore.showAuthModal"
    id="authentication-modal"
    tabindex="-1"
    aria-hidden="true"
    class="fixed top-0 right-0 left-0 z-50 justify-center items-center w-full md:inset-0 h-[calc(100%-1rem)] max-h-full"
    :class="{ flex: authStore.showAuthModal }"
  >
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-opacity-50 backdrop-blur-sm" @click="closeModal"></div>

    <div class="relative p-4 w-full max-w-md max-h-full z-10">
      <!-- Modal content -->
      <div
        class="relative bg-neutral-primary-soft border border-default rounded-base shadow-sm p-4 md:p-6"
      >
        <!-- Modal header -->
        <div class="flex items-center justify-between border-b border-default pb-4 md:pb-5">
          <h3 class="text-lg font-medium text-heading">
            {{
              authStore.isAuthenticated
                ? 'Account'
                : showLogin
                  ? 'Sign in to our platform'
                  : 'Create your account'
            }}
          </h3>
          <button
            type="button"
            @click="closeModal"
            class="text-body bg-transparent hover:bg-neutral-tertiary hover:text-heading rounded-base text-sm w-9 h-9 ms-auto inline-flex justify-center items-center transition-colors"
          >
            <svg
              class="w-5 h-5"
              aria-hidden="true"
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18 17.94 6M18 18 6.06 6"
              />
            </svg>
            <span class="sr-only">Close modal</span>
          </button>
        </div>

        <!-- User Info (when authenticated) -->
        <div v-if="authStore.isAuthenticated" class="pt-4 md:pt-6">
          <div class="text-center mb-6">
            <div
              class="w-16 h-16 bg-brand rounded-full mx-auto mb-4 flex items-center justify-center"
            >
              <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <h4 class="text-lg font-medium text-heading mb-1">
              {{ authStore.currentUser?.email }}
            </h4>
            <p class="text-sm text-body">
              <span v-if="authStore.currentUser?.is_verified" class="text-green-600"
                >✓ Verified</span
              >
              <span v-else class="text-yellow-600">⚠ Not Verified</span>
            </p>
          </div>

          <div class="space-y-3">
            <button
              @click="closeModal"
              class="w-full text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none transition-colors"
            >
              Close
            </button>
            <button
              @click="handleLogout"
              :disabled="authStore.isLoading"
              class="w-full text-white bg-red-600 box-border border border-transparent hover:bg-red-700 focus:ring-4 focus:ring-red-300 shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="authStore.isLoading" class="flex items-center justify-center">
                <svg
                  class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
                Signing out...
              </span>
              <span v-else>Sign Out</span>
            </button>
          </div>
        </div>

        <!-- Login/Signup Form -->
        <form v-else @submit="handleSubmit" class="pt-4 md:pt-6">
          <!-- Error Display -->
          <div v-if="authStore.error" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-base">
            <p class="text-sm text-red-600">{{ authStore.error }}</p>
          </div>

          <div class="mb-4">
            <label for="email" class="block mb-2.5 text-sm font-medium text-heading"
              >Your email</label
            >
            <input
              v-model="email"
              type="email"
              id="email"
              class="bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2.5 shadow-xs placeholder:text-body transition-colors"
              placeholder="example@company.com"
              required
              :disabled="isSubmitting || authStore.isLoading"
            />
          </div>

          <div class="mb-4">
            <label for="password" class="block mb-2.5 text-sm font-medium text-heading"
              >Your password</label
            >
            <input
              v-model="password"
              type="password"
              id="password"
              class="bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2.5 shadow-xs placeholder:text-body transition-colors"
              placeholder="•••••••••"
              required
              minlength="3"
              :disabled="isSubmitting || authStore.isLoading"
            />
          </div>

          <div v-if="!showLogin" class="mb-4">
            <label for="password" class="block mb-2.5 text-sm font-medium text-heading"
              >Deposite Money</label
            >
            <input
              v-model="money"
              type="number"
              id="money"
              class="bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand block w-full px-3 py-2.5 shadow-xs placeholder:text-body transition-colors"
              required
              minlength="3"
              :disabled="isSubmitting || authStore.isLoading"
            />
          </div>
          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="buttonDisabled"
            class="bg-brand box-border cursor-pointer border-amber-700 border hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none w-full mb-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span
              v-if="isSubmitting || authStore.isLoading"
              class="flex items-center justify-center"
            >
              <svg
                class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
              {{ showLogin ? 'Signing in...' : 'Creating account...' }}
            </span>
            <span v-else>
              {{ showLogin ? 'Login to your account' : 'Create your account' }}
            </span>
          </button>

          <!-- Toggle between login/signup -->
          <div class="text-sm font-medium text-body">
            {{ showLogin ? 'Not registered?' : 'Already have an account?' }}
            <button type="button" @click="toggleForm" class="text-fg-brand hover:underline ml-1">
              {{ showLogin ? 'Create account' : 'Sign in' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Custom animations and transitions */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
