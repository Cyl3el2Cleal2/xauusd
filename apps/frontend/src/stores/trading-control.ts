import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type TradingStatus = 'online' | 'pause' | 'stop'

export interface TradingControl {
  symbol: string
  displayName: string
  status: TradingStatus
}

export const useTradingControlStore = defineStore('trading-control', () => {
  // State
  const controls = ref<TradingControl[]>([
    { symbol: 'spot', displayName: 'Gold Spot', status: 'online' },
    { symbol: 'gold96', displayName: 'Gold 96', status: 'online' },
  ])

  const isLoading = ref(false)
  const saveMessage = ref('')
  const lastSavedAt = ref<Date | null>(null)

  // Getters
  const getControlBySymbol = computed(() => {
    return (symbol: string) => controls.value.find((c) => c.symbol === symbol)
  })

  const getControlsByStatus = computed(() => {
    return (status: TradingStatus) => controls.value.filter((c) => c.status === status)
  })

  const onlineControls = computed(() => getControlsByStatus.value('online'))
  const pausedControls = computed(() => getControlsByStatus.value('pause'))
  const stoppedControls = computed(() => getControlsByStatus.value('stop'))

  const hasOnlineControls = computed(() => onlineControls.value.length > 0)
  const hasPausedControls = computed(() => pausedControls.value.length > 0)
  const hasStoppedControls = computed(() => stoppedControls.value.length > 0)

  const isAllOnline = computed(() => controls.value.every((c) => c.status === 'online'))
  const isAllPaused = computed(() => controls.value.every((c) => c.status === 'pause'))
  const isAllStopped = computed(() => controls.value.every((c) => c.status === 'stop'))

  // Actions
  const updateStatus = (symbol: string, newStatus: TradingStatus) => {
    const control = controls.value.find((c) => c.symbol === symbol)
    if (control) {
      const oldStatus = control.status
      control.status = newStatus
      console.log(
        `[TradingControl] Status updated for ${control.displayName}: ${oldStatus} -> ${newStatus}`,
      )
    }
  }

  const setAllStatus = (status: TradingStatus) => {
    controls.value.forEach((control) => {
      control.status = status
    })
    console.log(`[TradingControl] All controls set to: ${status}`)
  }

  const resetToDefaults = () => {
    controls.value = [
      { symbol: 'spot', displayName: 'Gold Spot', status: 'online' },
      { symbol: 'gold96', displayName: 'Gold 96', status: 'online' },
    ]
    console.log('[TradingControl] Reset to default controls')
  }

  return {
    // State
    controls,
    isLoading,
    saveMessage,
    lastSavedAt,

    // Getters
    getControlBySymbol,
    getControlsByStatus,
    onlineControls,
    pausedControls,
    stoppedControls,
    hasOnlineControls,
    hasPausedControls,
    hasStoppedControls,
    isAllOnline,
    isAllPaused,
    isAllStopped,

    // Actions
    updateStatus,
    setAllStatus,
    resetToDefaults,
  }
})
