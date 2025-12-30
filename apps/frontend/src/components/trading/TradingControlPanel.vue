<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  useTradingControlStore,
  type TradingControl,
  type TradingStatus,
} from '@/stores/trading-control'

// Store
const tradingControlStore = useTradingControlStore()
interface Props {
  initiallyCollapsed?: boolean
  showBulkActions?: boolean
}

// Props with defaults
const props = withDefaults(defineProps<Props>(), {
  initiallyCollapsed: false,
  showBulkActions: true,
})

// Local state
const isControlPanelCollapsed = ref(props.initiallyCollapsed)

// Computed properties from store
const controls = computed(() => tradingControlStore.controls)

// Store getters
const onlineControls = computed(() => tradingControlStore.onlineControls)
const pausedControls = computed(() => tradingControlStore.pausedControls)
const stoppedControls = computed(() => tradingControlStore.stoppedControls)
const hasOnlineControls = computed(() => tradingControlStore.hasOnlineControls)
const hasPausedControls = computed(() => tradingControlStore.hasPausedControls)
const hasStoppedControls = computed(() => tradingControlStore.hasStoppedControls)

// Methods
const updateTradingStatus = (symbol: string, newStatus: TradingStatus) => {
  tradingControlStore.updateStatus(symbol, newStatus)
}

const toggleControlPanel = () => {
  isControlPanelCollapsed.value = !isControlPanelCollapsed.value
}

// Utility functions
const getStatusColor = (status: TradingStatus) => {
  switch (status) {
    case 'online':
      return 'bg-green-500'
    case 'pause':
      return 'bg-yellow-500'
    case 'stop':
      return 'bg-red-500'
    default:
      return 'bg-gray-500'
  }
}

const getStatusBadgeColor = (status: TradingStatus) => {
  switch (status) {
    case 'online':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'pause':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'stop':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

const formatLastSavedTime = (date: Date | null) => {
  if (!date) return ''
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}
</script>

<template>
  <div class="p-4 bg-white rounded-lg border border-neutral-200">
    <!-- Header with collapse toggle and save button -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-3">
        <button
          @click="toggleControlPanel"
          class="flex items-center gap-2 text-sm font-semibold text-heading hover:text-gray-600 transition-colors"
        >
          <svg
            :class="`w-4 h-4 transform transition-transform ${isControlPanelCollapsed ? 'rotate-0' : 'rotate-180'}`"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            ></path>
          </svg>
          <h6>Trading Control</h6>
          <!-- Status indicators -->
          <div class="flex items-center gap-1 ml-2">
            <span class="flex items-center gap-1 text-xs text-green-600" v-if="hasOnlineControls">
              <span class="w-2 h-2 bg-green-500 rounded-full"></span>
              {{ onlineControls.length }} Online
            </span>
            <span class="flex items-center gap-1 text-xs text-yellow-600" v-if="hasPausedControls">
              <span class="w-2 h-2 bg-yellow-500 rounded-full"></span>
              {{ pausedControls.length }} Paused
            </span>
            <span class="flex items-center gap-1 text-xs text-red-600" v-if="hasStoppedControls">
              <span class="w-2 h-2 bg-red-500 rounded-full"></span>
              {{ stoppedControls.length }} Stopped
            </span>
          </div>
        </button>
      </div>
    </div>

    <!-- Collapsible content -->
    <div
      :class="`transition-all duration-300 ease-in-out ${
        isControlPanelCollapsed ? 'max-h-0 opacity-0 overflow-hidden' : 'max-h-96 opacity-100'
      }`"
    >
      <!-- Individual controls -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="control in controls"
          :key="control.symbol"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
        >
          <div class="flex items-center gap-3">
            <div :class="`w-3 h-3 ${getStatusColor(control.status)} rounded-full`"></div>
            <div>
              <div class="font-medium text-sm text-heading">{{ control.displayName }}</div>
              <div class="text-xs text-body">{{ control.symbol.toUpperCase() }}</div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span
              :class="`px-2 py-1 text-xs font-medium rounded-full border ${getStatusBadgeColor(control.status)}`"
            >
              {{ control.status.toUpperCase() }}
            </span>
            <div class="flex gap-1">
              <button
                @click="updateTradingStatus(control.symbol, 'online')"
                :class="`px-2 py-1 text-xs font-medium rounded ${
                  control.status === 'online'
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                } transition-colors`"
              >
                Online
              </button>
              <button
                @click="updateTradingStatus(control.symbol, 'pause')"
                :class="`px-2 py-1 text-xs font-medium rounded ${
                  control.status === 'pause'
                    ? 'bg-yellow-500 text-white'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                } transition-colors`"
              >
                Pause
              </button>
              <button
                @click="updateTradingStatus(control.symbol, 'stop')"
                :class="`px-2 py-1 text-xs font-medium rounded ${
                  control.status === 'stop'
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                } transition-colors`"
              >
                Stop
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
