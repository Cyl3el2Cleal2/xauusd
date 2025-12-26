<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import OrderDetail from './OrderDetail.vue'
import {
  formatThaiCurrency,
  formatGoldAmount,
  formatTimestamp,
  getTransactionTypeClass,
  getTransactionIcon,
  getStatusBadgeClass,
  type Transaction,
} from '@/utils'

const authStore = useAuthStore()

// Sample user transaction data
const transactions = ref<Transaction[]>([
  {
    id: 'TXN001',
    type: 'buy',
    amount: 5.2,
    price: 1942.5,
    total: 10101.0,
    timestamp: '2024-01-15T14:32:00Z',
    status: 'completed',
    fee: 2.55,
  },
  {
    id: 'TXN002',
    type: 'sell',
    amount: 3.8,
    price: 1945.75,
    total: 7393.85,
    timestamp: '2024-01-15T11:20:00Z',
    status: 'completed',
    fee: 1.85,
  },
  {
    id: 'TXN003',
    type: 'buy',
    amount: 10.0,
    price: 1941.25,
    total: 19412.5,
    timestamp: '2024-01-14T16:45:00Z',
    status: 'completed',
    fee: 4.9,
  },
  {
    id: 'TXN004',
    type: 'sell',
    amount: 7.5,
    price: 1943.8,
    total: 14578.5,
    timestamp: '2024-01-14T09:15:00Z',
    status: 'pending',
    fee: 3.64,
  },
  {
    id: 'TXN005',
    type: 'buy',
    amount: 2.3,
    price: 1940.9,
    total: 4464.07,
    timestamp: '2024-01-13T13:52:00Z',
    status: 'completed',
    fee: 1.12,
  },
])

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
        <a
          href="#"
          class="font-medium text-sm p-2 bg-orange-400 rounded-full text-fg-brand hover:underline"
          >New Order</a
        >
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
      <div class="flex items-center justify-between">
        <div class="text-sm text-body">Showing {{ transactions.length }} recent transactions</div>
        <button class="font-medium text-fg-brand hover:underline text-sm">
          Load More Transactions
        </button>
      </div>
    </div>
  </div>
</template>
