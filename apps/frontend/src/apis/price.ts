import apiClient from './api'
import { ref, type Ref } from 'vue'
const api = apiClient
type golds = 'spot' | 'gold96'
export interface SpotPrice {
  symbol: string
  price: string
  time: number
  type: string
}

export interface GoldTradePrice {
  symbol: string
  buy_price: string
  sell_price: string
  time: number
  type: string
}

// Singleton instance for shared state
const baseURL = api.defaults.baseURL
const gold96Price = ref<GoldTradePrice | null>(null)
const goldSpotPrice = ref<SpotPrice | null>(null)
const activeStreams = new Map<golds, EventSource>()

const usePrice = () => {
  const streamSymbol = (price: Ref, symbol: golds) => {
    // Close existing stream if it exists
    if (activeStreams.has(symbol)) {
      activeStreams.get(symbol)?.close()
    }

    const stream = new EventSource(`${baseURL}/stream/price/${symbol}`)
    activeStreams.set(symbol, stream)

    stream.onmessage = (event) => {
      try {
        // Parse JSON data from SSE
        const parsedData = JSON.parse(event.data)
        price.value = parsedData
      } catch (error) {
        console.error('Error parsing SSE data:', error)
        // Fallback to raw string if parsing fails
        price.value = event.data
      }
    }

    stream.onerror = (error) => {
      console.error(`Stream error for ${symbol}:`, error)
      activeStreams.delete(symbol)
    }
  }

  return { gold96Price, goldSpotPrice, streamSymbol }
}

export { usePrice }
