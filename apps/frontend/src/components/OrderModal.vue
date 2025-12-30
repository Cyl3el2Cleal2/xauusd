<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { usePrice } from '@/apis/price'
import { tradeApi, type TradeRequest, type Balance, type Portfolio } from '@/apis/order'
import { formatThaiCurrency, formatGoldAmount } from '@/utils'

// Props and emits
interface Props {
  isOpen: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'open'): void
  (e: 'trade-success', trade: any): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Store and composables
const authStore = useAuthStore()
const { gold96Price } = usePrice()

// Modal state
const orderType = ref<'buy' | 'sell'>('buy')
const amount = ref('')
const isSubmitting = ref(false)
const error = ref('')
const successMessage = ref('')
const balance = ref<Portfolio | Balance | null>(null)
const isLoadingBalance = ref(false)

// Form validation
const amountError = ref('')

// Computed properties
const currentMarketPrice = computed(() => {
  if (!gold96Price.value?.buy_price) return null
  return {
    buy: parseFloat(gold96Price.value.buy_price),
    sell: parseFloat(gold96Price.value.sell_price),
  }
})

const calculatedGoldAmount = computed(() => {
  if (!amount.value || !currentMarketPrice.value) return 0
  const amountBaht = parseFloat(amount.value)
  const pricePerOz =
    orderType.value === 'buy' ? currentMarketPrice.value.buy : currentMarketPrice.value.sell
  return amountBaht / pricePerOz
})

const isFormValid = computed(() => {
  return amount.value && !amountError.value && parseFloat(amount.value) > 0
})

const buttonDisabled = computed(() => {
  return (
    !isFormValid.value || isSubmitting.value || authStore.isLoading || !currentMarketPrice.value
  )
})

// Watch for modal open to reset form and fetch balance
watch(
  () => props.isOpen,
  (newValue) => {
    if (newValue) {
      resetForm()
      fetchBalance()
    }
  },
)

// Watch for order type change
watch(orderType, () => {
  validateAmount()
})

// Watch for amount changes
watch(amount, () => {
  validateAmount()
})

// Fetch user balance
const fetchBalance = async () => {
  if (!authStore.isAuthenticated) return

  isLoadingBalance.value = true
  try {
    balance.value = await tradeApi.getPort()
  } catch (err: any) {
    console.error('Failed to fetch balance:', err)
    // Don't show error to user for balance fetch failure
  } finally {
    isLoadingBalance.value = false
  }
}

// Validation functions
const validateAmount = () => {
  if (!amount.value) {
    amountError.value = 'Amount is required'
    return false
  }

  const amountNum = parseFloat(amount.value)
  if (isNaN(amountNum) || amountNum <= 0) {
    amountError.value = 'Please enter a valid amount'
    return false
  }

  if (amountNum < 1000) {
    amountError.value = 'Minimum order is ฿1,000'
    return false
  }

  // Check if user has sufficient balance for buy orders
  if (orderType.value === 'buy' && balance.value) {
    const maxAvailable =
      'available_balance' in balance.value ? balance.value.available_balance : balance.value.balance
    if (amountNum > maxAvailable) {
      amountError.value = `Insufficient balance. Available: ${formatThaiCurrency(maxAvailable)}`
      return false
    }
  }

  // Check if user has sufficient gold for sell orders
  if (orderType.value === 'sell' && balance.value) {
    const goldAvailable =
      'gold_holdings' in balance.value
        ? balance.value.gold_holdings
        : balance.value.holdings.gold96_baht
    const goldToSell = calculatedGoldAmount.value
    if (goldToSell > goldAvailable) {
      amountError.value = `Insufficient gold. Available: ${formatGoldAmount(goldAvailable)}`
      return false
    }
  }

  if (amountNum > 1000000) {
    amountError.value = 'Maximum order is ฿1,000,000'
    return false
  }

  amountError.value = ''
  return true
}

// Form submission
const handleSubmit = async (e: Event) => {
  e.preventDefault()

  if (!isFormValid.value || !currentMarketPrice.value) return

  isSubmitting.value = true
  error.value = ''
  successMessage.value = ''

  try {
    const amountBaht = parseFloat(amount.value)

    const tradeData: TradeRequest = {
      symbol: 'gold96',
      amount: amountBaht,
    }

    const trade =
      orderType.value === 'buy'
        ? await tradeApi.buyGold(tradeData)
        : await tradeApi.sellGold(tradeData)

    successMessage.value = `Trade placed successfully! Trade ID: ${trade.id}`
    emit('trade-success', trade)

    // Refresh balance after successful trade
    // await fetchBalance()

    // Reset form after successful submission
    setTimeout(() => {
      resetForm()
      emit('close')
    }, 800)
  } catch (err: any) {
    console.error('Trade creation error:', err)
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else if (err.response?.data?.message) {
      error.value = err.response.data.message
    } else {
      error.value = 'Failed to place trade. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}

const resetForm = () => {
  amount.value = ''
  amountError.value = ''
  error.value = ''
  successMessage.value = ''
}

const openModal = () => {
  emit('open')
}

const closeModal = () => {
  if (!isSubmitting.value) {
    emit('close')
    resetForm()
  }
}

const switchOrderType = (type: 'buy' | 'sell') => {
  orderType.value = type
  validateAmount()
}

// Handle backdrop click
const handleBackdropClick = (event: MouseEvent) => {
  if (event.target === event.currentTarget) {
    closeModal()
  }
}
</script>

<template>
  <!-- Trade Button -->
  <button
    @click="openModal"
    class="text-white bg-brand box-border border border-transparent hover:bg-brand-strong focus:ring-4 focus:ring-brand-medium shadow-xs font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none"
    type="button"
  >
    New Trade
  </button>

  <!-- Main modal -->
  <div
    v-show="isOpen"
    id="trade-modal"
    tabindex="-1"
    aria-hidden="true"
    class="fixed top-0 right-0 left-0 z-50 justify-center items-center w-full md:inset-0 h-[calc(100%-1rem)] max-h-full"
    :class="{ flex: isOpen }"
  >
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-opacity-50 backdrop-blur-sm" @click="handleBackdropClick"></div>

    <div class="relative p-4 w-full max-w-lg max-h-full z-10">
      <!-- Modal content -->
      <div
        class="relative bg-neutral-primary-soft border border-default rounded-base shadow-sm p-4 md:p-6"
      >
        <!-- Modal header -->
        <div class="flex items-center justify-between border-b border-default pb-4 md:pb-5">
          <h3 class="text-lg font-medium text-heading">New Trade</h3>
          <button
            type="button"
            @click="closeModal"
            class="text-body bg-transparent hover:bg-neutral-tertiary hover:text-heading rounded-base text-sm w-9 h-9 ms-auto inline-flex justify-center items-center transition-colors"
            :disabled="isSubmitting"
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

        <!-- Balance Display -->
        <div class="mt-4 mb-4 p-4 bg-blue-50 border border-blue-200 rounded-base">
          <div v-if="isLoadingBalance" class="flex items-center justify-center py-2">
            <svg
              class="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-500"
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
            <span class="text-sm text-blue-600">Loading balance...</span>
          </div>
          <div v-else-if="balance" class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div class="text-gray-600 mb-1">Available Balance</div>
              <div class="font-semibold text-gray-900">
                {{
                  formatThaiCurrency(
                    'balance' in balance ? balance.balance : balance.available_balance,
                  )
                }}
              </div>
            </div>
            <div>
              <div class="text-gray-600 mb-1">Gold Holdings</div>
              <div class="font-semibold text-gray-900">
                {{
                  formatThaiCurrency(
                    'holdings_value' in balance
                      ? balance.holdings_value.gold96
                      : balance.gold_holdings,
                  )
                }}
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-gray-600 text-center">Balance unavailable</div>
        </div>

        <!-- Order Type Selection -->
        <div class="flex rounded-base overflow-hidden mb-4">
          <button
            @click="switchOrderType('buy')"
            :class="[
              'flex-1 py-3 px-4 font-medium transition-colors',
              orderType === 'buy'
                ? 'bg-green-600 text-white'
                : 'bg-neutral-secondary-medium text-heading hover:bg-neutral-tertiary',
            ]"
            :disabled="isSubmitting"
          >
            Buy Gold
          </button>
          <button
            @click="switchOrderType('sell')"
            :class="[
              'flex-1 py-3 px-4 font-medium transition-colors',
              orderType === 'sell'
                ? 'bg-red-600 text-white'
                : 'bg-neutral-secondary-medium text-heading hover:bg-neutral-tertiary',
            ]"
            :disabled="isSubmitting"
          >
            Sell Gold
          </button>
        </div>

        <!-- Market Price Display -->
        <div
          v-if="currentMarketPrice"
          class="mb-4 p-4 bg-neutral-tertiary border border-default rounded-base"
        >
          <div class="text-sm font-medium text-heading mb-2">Current Market Price (Gold96)</div>
          <div class="flex justify-between">
            <div>
              <span class="text-xs text-body">Buy:</span>
              <span class="ml-2 font-medium text-green-600">
                {{ formatThaiCurrency(currentMarketPrice.buy) }}
              </span>
            </div>
            <div>
              <span class="text-xs text-body">Sell:</span>
              <span class="ml-2 font-medium text-red-600">
                {{ formatThaiCurrency(currentMarketPrice.sell) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Trade Form -->
        <form @submit="handleSubmit" class="space-y-4">
          <!-- Success Message -->
          <div v-if="successMessage" class="p-3 bg-green-50 border border-green-200 rounded-base">
            <p class="text-sm text-green-600">{{ successMessage }}</p>
          </div>

          <!-- Error Message -->
          <div v-if="error" class="p-3 bg-red-50 border border-red-200 rounded-base">
            <p class="text-sm text-red-600">{{ error }}</p>
          </div>

          <!-- Amount Field -->
          <div>
            <label for="amount" class="block mb-2.5 text-sm font-medium text-heading">
              Amount (Thai Baht)
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <span class="text-gray-500 text-sm">฿</span>
              </div>
              <input
                id="amount"
                v-model="amount"
                type="number"
                step="0.01"
                min="1000"
                max="1000000"
                @blur="validateAmount"
                @input="validateAmount"
                :disabled="isSubmitting || authStore.isLoading || !currentMarketPrice"
                class="bg-neutral-secondary-medium border border-default-medium text-heading text-sm rounded-base focus:ring-brand focus:border-brand block w-full pl-8 pr-3 py-2.5 shadow-xs placeholder:text-body transition-colors"
                placeholder="Enter amount in Thai Baht"
              />
            </div>
            <p v-if="amountError" class="mt-1 text-sm text-red-600">{{ amountError }}</p>
          </div>

          <!-- Gold Amount Calculation -->
          <div
            v-if="currentMarketPrice && amount"
            class="p-4 bg-neutral-tertiary border border-default rounded-base"
          >
            <div class="flex justify-between items-center">
              <span class="text-sm font-medium text-heading">
                You will {{ orderType === 'buy' ? 'receive' : 'sell' }}:
              </span>
              <span class="text-lg font-bold text-blue-600">
                {{ formatGoldAmount(calculatedGoldAmount) }}
              </span>
            </div>
            <div class="text-xs text-body mt-1">
              At {{ orderType === 'buy' ? 'buy' : 'sell' }} price of
              {{
                formatThaiCurrency(
                  orderType === 'buy' ? currentMarketPrice.buy : currentMarketPrice.sell,
                )
              }}
            </div>
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="buttonDisabled"
            :class="[
              'w-full text-white font-medium leading-5 rounded-base text-sm px-4 py-2.5 focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
              orderType === 'buy'
                ? 'bg-green-600 hover:bg-green-700'
                : 'bg-red-600 hover:bg-red-700',
            ]"
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
              {{
                orderType === 'buy'
                  ? isSubmitting
                    ? 'Placing Buy Order...'
                    : 'Place Buy Order'
                  : isSubmitting
                    ? 'Placing Sell Order...'
                    : 'Place Sell Order'
              }}
            </span>
            <span v-else>
              {{ orderType === 'buy' ? 'Place Buy Order' : 'Place Sell Order' }}
            </span>
          </button>
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
