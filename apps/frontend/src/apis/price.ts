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

const usePrice = () => {
  const baseURL = api.defaults.baseURL
  const gold96Price = ref<GoldTradePrice | null>(null)
  const goldSpotPrice = ref<SpotPrice | null>(null)

  const streamSymbol = (price: Ref, symbol: golds) => {
    const stream = new EventSource(`${baseURL}/stream/price/${symbol}`)
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
  }

  return { gold96Price, goldSpotPrice, streamSymbol }
}

export { usePrice }
