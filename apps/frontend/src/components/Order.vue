<script setup lang="ts">
// Add component name to satisfy multi-word requirement
defineOptions({
  name: 'TradingOrder',
})
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import OrderDetail from './OrderDetail.vue'
import OrderModal from './OrderModal.vue'
import { tradeApi, type TradingHistoryResponse, type TradeResponse } from '@/apis/order'
import TradingControlPanel from './trading/TradingControlPanel.vue'
import { formatThaiCurrency, formatGoldAmount, type Transaction } from '@/utils'

const authStore = useAuthStore()

// Modal state
const showOrderModal = ref(false)

// Transaction state
const transactions = ref<Transaction[]>([])
const isLoading = ref(false)
const error = ref('')
const currentPage = ref(0)
const hasMore = ref(true)
const pageSize = 50

// Polling state
const pollingOrders = ref<Set<string>>(new Set())

// Trading control store will be used directly in the component

// Transform API response to Transaction interface
const transformTransaction = (apiData: TradeResponse): Transaction => {
  return {
    id: apiData.id,
    type: apiData.transaction_type,
    symbol: apiData.symbol,
    amount: apiData.quantity,
    price: apiData.price_per_unit,
    total: apiData.total_amount,
    timestamp: apiData.created_at,
    status: apiData.status,
    fee: apiData.fee || 0,
  }
}

// Fetch trading history
const fetchTradingHistory = async (reset: boolean = false) => {
  if (!authStore.isAuthenticated) {
    transactions.value = []
    return
  }

  if (isLoading.value || (!hasMore.value && !reset)) return

  isLoading.value = true
  error.value = ''

  try {
    const offset = reset ? 0 : currentPage.value * pageSize
    const historyData = await tradeApi.getTradingHistory(pageSize, offset)

    const transformedData = historyData.map(transformTransaction)

    if (reset) {
      transactions.value = transformedData
      currentPage.value = 0
    } else {
      transactions.value.push(...transformedData)
    }

    currentPage.value++
    hasMore.value = historyData.length === pageSize
  } catch (err: unknown) {
    console.error('Failed to fetch trading history:', err)
    const errorResponse = err as { response?: { data?: { message?: string } } }
    error.value = errorResponse.response?.data?.message || 'Failed to load transactions'
  } finally {
    isLoading.value = false
  }
}

// Load more transactions
const loadMore = () => {
  fetchTradingHistory(false)
}

// Refresh transactions
const refreshTransactions = () => {
  fetchTradingHistory(true)
}

// Calculate total bought and sold
const totalBought = computed(() => {
  return transactions.value
    .filter((t) => t.type === 'buy' && t.status === 'completed')
    .reduce((sum, t) => sum + t.amount, 0)
})

const totalSold = computed(() => {
  return transactions.value
    .filter((t) => t.type === 'sell' && t.status === 'completed')
    .reduce((sum, t) => sum + t.amount, 0)
})

// Calculate net position
const netPosition = computed(() => {
  return totalBought.value - totalSold.value
})

// Calculate P&L
const totalPnL = computed(() => {
  const buys = transactions.value
    .filter((t) => t.type === 'buy' && t.status === 'completed')
    .reduce((sum, t) => sum + t.total, 0)

  const sells = transactions.value
    .filter((t) => t.type === 'sell' && t.status === 'completed')
    .reduce((sum, t) => sum + t.total, 0)

  return sells - buys
})

// Modal handlers
const openOrderModal = () => {
  if (authStore.isAuthenticated) {
    showOrderModal.value = true
  } else {
    // If not authenticated, show login modal
    authStore.toggleAuthModal()
  }
}

const closeOrderModal = () => {
  showOrderModal.value = false
}

const handleTradeSuccess = (trade: TradeResponse) => {
  // Add the new transaction to the list
  const newTransaction: Transaction = {
    id: trade.id,
    symbol: trade.symbol,
    type: trade.type || trade.transaction_type,
    amount: trade.amount || trade.quantity,
    price: trade.price || trade.price_per_unit,
    total: trade.total || trade.total_amount,
    timestamp: trade.created_at,
    status: trade.status,
    fee: trade.fee || 0,
  }

  // Add to the beginning of the transactions array
  transactions.value.unshift(newTransaction)

  // Start polling if the order is in processing status
  if (trade.status === 'processing') {
    pollOrderStatus(trade.id)
  }
}

// Poll order status until completion
const pollOrderStatus = async (orderId: string) => {
  // Avoid polling the same order multiple times
  if (pollingOrders.value.has(orderId)) {
    return
  }

  pollingOrders.value.add(orderId)

  try {
    const finalStatus = await tradeApi.pollOrderUntilComplete(
      orderId,
      3000, // Poll every 3 seconds
      60, // Maximum 60 attempts (3 minute total)
    )

    // Fetch final transaction details when completed or failed
    if (finalStatus.status === 'completed' || finalStatus.status === 'failed') {
      const transactionDetail = await tradeApi.getTradeById(orderId)

      // Update the transaction in the list with detailed information
      const transactionIndex = transactions.value.findIndex((t) => t.id === orderId)
      if (transactionIndex !== -1) {
        const currentTransaction = transactions.value[transactionIndex]
        if (!currentTransaction) return

        // Safely parse numeric values
        const safeParseNumber = (value: any, fallback: number) => {
          if (value === null || value === undefined || value === '') return fallback
          const parsed = parseFloat(value)
          return isNaN(parsed) ? fallback : parsed
        }

        // Parse values safely using correct API property names
        const newAmount = safeParseNumber(transactionDetail.quantity, currentTransaction.amount)
        const newPrice = safeParseNumber(transactionDetail.price_per_unit, currentTransaction.price)
        const newTotal = safeParseNumber(transactionDetail.total_amount, currentTransaction.total)
        const newFee = safeParseNumber(transactionDetail.fee, currentTransaction.fee)

        // Create a new transaction object with updated values
        const updatedTransaction: Transaction = {
          id: currentTransaction.id,
          type: transactionDetail.transaction_type || currentTransaction.type,
          symbol: transactionDetail.symbol || currentTransaction.symbol,
          status: transactionDetail.status,
          // Update with safely parsed values using correct API properties
          amount: newAmount,
          price: newPrice,
          total: newTotal,
          fee: newFee,
          timestamp: currentTransaction.timestamp,
          updated_at: transactionDetail.updated_at || currentTransaction.updated_at,
        }

        // Use splice for reactivity
        transactions.value.splice(transactionIndex, 1, updatedTransaction)
      }
    }
  } catch (error) {
    console.error(`Failed to poll order ${orderId}:`, error)
    // Update the transaction status to failed if polling fails
    const transactionIndex = transactions.value.findIndex((t) => t.id === orderId)
    if (transactionIndex !== -1) {
      const currentTransaction = transactions.value[transactionIndex]
      if (currentTransaction) {
        const failedTransaction: Transaction = {
          ...currentTransaction,
          status: 'failed' as const,
        }
        // Use splice for reactivity
        transactions.value.splice(transactionIndex, 1, failedTransaction)
      }
    }
  } finally {
    pollingOrders.value.delete(orderId)
  }
}

// Check for processing orders and start polling them
const startPollingProcessingOrders = () => {
  transactions.value.forEach((transaction) => {
    if (transaction.status === 'processing' && !pollingOrders.value.has(transaction.id)) {
      pollOrderStatus(transaction.id)
    }
  })
}

// Fetch transactions on component mount
onMounted(() => {
  fetchTradingHistory(true)
})

// Start polling for any processing orders after fetching
watch(
  () => transactions.value,
  () => {
    startPollingProcessingOrders()
  },
  { deep: true },
)

// Watch for authentication changes
watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      fetchTradingHistory(true)
    } else {
      transactions.value = []
    }
  },
)
</script>

<template>
  <div
    class="w-full max-w-5xl p-6 bg-neutral-primary-soft border border-default rounded-base shadow-xs"
  >
    <!-- Header -->
    <div class="mb-6">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-yellow-400 rounded-full"></div>
            <h5 class="text-xl font-semibold leading-none text-heading">Gold Trading</h5>
          </div>
        </div>

        <button
          @click="openOrderModal"
          class="font-medium text-sm p-2 bg-orange-400 rounded-full text-fg-brand hover:bg-orange-500 transition-colors"
        >
          New Trade
        </button>
      </div>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="p-4 bg-white rounded-lg border border-neutral-200">
          <div class="text-sm text-body mb-1">Total Bought</div>
          <div class="text-lg font-semibold text-green-600">
            {{ formatGoldAmount(totalBought) }}
          </div>
        </div>
        <div class="p-4 bg-white rounded-lg border border-neutral-200">
          <div class="text-sm text-body mb-1">Total Sold</div>
          <div class="text-lg font-semibold text-red-600">{{ formatGoldAmount(totalSold) }}</div>
        </div>
        <div class="p-4 bg-white rounded-lg border border-neutral-200">
          <div class="text-sm text-body mb-1">Net Position</div>
          <div class="text-lg font-semibold text-heading">{{ formatGoldAmount(netPosition) }}</div>
        </div>
        <div class="p-4 bg-white rounded-lg border border-neutral-200">
          <div class="text-sm text-body mb-1">Total P&L</div>
          <div
            :class="totalPnL >= 0 ? 'text-green-600' : 'text-red-600'"
            class="text-lg font-semibold"
          >
            {{ formatThaiCurrency(totalPnL) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Trading Control Panel -->
    <div class="mb-6">
      <TradingControlPanel />
    </div>

    <!-- Transaction List -->
    <div class="flow-root">
      <div class="space-y-2">
        <!-- Header -->
        <div
          class="grid grid-cols-6 gap-4 pb-3 border-b border-default text-xs font-medium text-body uppercase tracking-wide"
        >
          <div>Transaction</div>
          <div>Type</div>
          <div>Amount</div>
          <div>Price</div>
          <div>Total</div>
          <div class="text-right">Status</div>
        </div>

        <!-- Transaction Items -->
        <ul role="list" class="divide-y divide-default">
          <OrderDetail
            v-for="transaction in transactions"
            :key="transaction.id"
            :transaction="transaction"
          />
        </ul>
      </div>
    </div>

    <!-- Footer with pagination or load more -->
    <div class="mt-6 pt-4 border-t border-default">
      <!-- Loading state -->
      <div
        v-if="isLoading && transactions.length === 0"
        class="flex items-center justify-center py-8"
      >
        <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24">
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
        <span class="text-sm text-gray-600">Loading transactions...</span>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="flex items-center justify-between py-4">
        <div class="text-sm text-red-600">{{ error }}</div>
        <button
          @click="refreshTransactions"
          class="font-medium text-fg-brand hover:underline text-sm"
        >
          Retry
        </button>
      </div>

      <!-- Empty state -->
      <div v-else-if="transactions.length === 0" class="flex items-center justify-between py-4">
        <div class="text-sm text-gray-600">No transactions found</div>
        <button
          @click="refreshTransactions"
          class="font-medium text-fg-brand hover:underline text-sm"
        >
          Refresh
        </button>
      </div>

      <!-- Normal state with transactions -->
      <div v-else class="flex items-center justify-between">
        <div class="text-sm text-body">
          Showing {{ transactions.length }} transaction{{ transactions.length !== 1 ? 's' : '' }}
          <span v-if="!hasMore" class="text-gray-500">(showing all)</span>
        </div>
        <div class="flex gap-2">
          <button
            @click="refreshTransactions"
            class="font-medium text-fg-brand hover:underline text-sm"
          >
            Refresh
          </button>
          <button
            v-if="hasMore && !isLoading"
            @click="loadMore"
            class="font-medium text-fg-brand hover:underline text-sm"
          >
            Load More
          </button>
          <button v-if="hasMore && isLoading" disabled class="font-medium text-gray-400 text-sm">
            Loading...
          </button>
        </div>
      </div>
    </div>

    <!-- Order Modal -->
    <OrderModal
      :is-open="showOrderModal"
      @close="closeOrderModal"
      @trade-success="handleTradeSuccess"
    />
  </div>
</template>
