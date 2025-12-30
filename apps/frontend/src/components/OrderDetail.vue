<script setup lang="ts">
import {
  formatThaiCurrency,
  formatGoldAmount,
  formatTimestamp,
  getTransactionTypeClass,
  getTransactionIcon,
  getStatusBadgeClass,
  type Transaction,
} from '@/utils'

interface Props {
  transaction: Transaction
}

defineProps<Props>()
</script>

<template>
  <li class="py-3 sm:py-3 hover:bg-neutral-primary-50 transition-colors cursor-pointer">
    <div class="grid grid-cols-6 gap-4 items-center">
      <!-- Transaction ID & Time -->
      <div>
        <!-- <div class="font-medium text-heading text-sm">{{ transaction.id }}</div> -->
        <div class="text-xs text-body">{{ formatTimestamp(transaction.timestamp) }}</div>
      </div>

      <!-- Transaction Type -->
      <div class="flex items-center gap-1">
        <span :class="getTransactionTypeClass(transaction.type)" class="text-lg">
          {{ getTransactionIcon(transaction.type) }}
        </span>
        <span :class="getTransactionTypeClass(transaction.type)" class="text-sm font-medium capitalize">
          {{ transaction.type }}
        </span>
        <span class="uppercase text-sm px-1 bg-orange-400 rounded-full">

        {{ transaction.symbol }}
        </span>
      </div>

      <!-- Amount -->
      <div>
        <div class="font-medium text-heading">
          {{ transaction.amount ? formatGoldAmount(transaction.amount) : '-' }}
        </div>
        <div class="text-xs text-body">Baht</div>
      </div>

      <!-- Price -->
      <div>
        <div class="font-medium text-heading">
          {{ transaction.price ? formatThaiCurrency(transaction.price) : '...' }}
        </div>
        <div class="text-xs text-body">per Baht</div>
      </div>

      <!-- Total -->
      <div>
        <div class="font-medium text-heading">{{ formatThaiCurrency(transaction.total) }}</div>
      </div>

      <!-- Status -->
      <div class="text-right">
        <span
          :class="getStatusBadgeClass(transaction.status)"
          class="px-2 py-1 text-xs font-medium rounded-full capitalize"
        >
          {{ transaction.status }}
        </span>
      </div>
    </div>
  </li>
</template>
