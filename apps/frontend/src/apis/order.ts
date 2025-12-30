import apiClient from './api'

export interface TradeRequest {
  symbol: string
  amount: number
}

export interface TradeResponse {
  id: string
  symbol: string
  type: 'buy' | 'sell'
  amount: number
  price: number
  total: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  fee: number
  created_at: string
  updated_at: string
}

export interface TradingHistoryResponse {
  user_id: string
  symbol: string
  transaction_type: 'buy' | 'sell'
  quantity: number
  price_per_unit: number
  total_amount: number
  status: 'pending' | 'completed' | 'failed'
  id: string
  created_at: string
  updated_at: string
  processing_id: string
  poll_url: string
  error_message?: string
}

export interface Balance {
  available_balance: number
  total_balance: number
  gold_holdings: number
  currency: string
}

export interface Portfolio {
  user_id: string
  balance: number
  holdings: Holdings
  holdings_value: HoldingsValue
  total_portfolio_value: number
  currency: string
  timestamp: string
  current_prices: CurrentPrices
}

export interface Holdings {
  spot_grams: number
  gold96_baht: number
}

export interface HoldingsValue {
  spot: number
  gold96: number
}

export interface CurrentPrices {
  spot: number
  gold96: Gold96
}

export interface Gold96 {
  buy: number
  sell: number
}

export const tradeApi = {
  /**
   * Buy gold
   */
  buyGold: async (tradeData: TradeRequest): Promise<TradeResponse> => {
    const response = await apiClient.post<TradeResponse>('/trading/buy', tradeData)
    return response.data
  },

  /**
   * Sell gold
   */
  sellGold: async (tradeData: TradeRequest): Promise<TradeResponse> => {
    const response = await apiClient.post<TradeResponse>('/trading/sell', tradeData)
    return response.data
  },

  /**
   * Get user's trades
   */
  getTrades: async (symbol?: string): Promise<TradeResponse[]> => {
    const params = symbol ? { symbol } : {}
    const response = await apiClient.get<TradeResponse[]>('/trades', { params })
    return response.data
  },

  /**
   * Get trade by ID
   */
  getTradeById: async (tradeId: string): Promise<TradeResponse> => {
    const response = await apiClient.get<TradeResponse>(`/trading/transaction/${tradeId}`)
    return response.data
  },

  /**
   * Get user's balance
   */
  getBalance: async (): Promise<Balance> => {
    const response = await apiClient.get<Balance>('/trading/balance')
    return response.data
  },

  getPort: async (): Promise<Portfolio> => {
    const response = await apiClient.get<Portfolio>('/trading/portfolio')
    return response.data
  },

  /**
   * Get trading history with pagination
   */
  getTradingHistory: async (
    limit: number = 50,
    offset: number = 0,
  ): Promise<TradingHistoryResponse[]> => {
    const response = await apiClient.get<TradingHistoryResponse[]>('/trading/history', {
      params: { limit, offset },
    })
    return response.data
  },

  /**
   * Poll order status
   */
  pollOrderStatus: async (orderId: string): Promise<TradingHistoryResponse> => {
    const response = await apiClient.get<TradingHistoryResponse>(`/trading/poll/${orderId}`)
    return response.data
  },

  /**
   * Poll order status with interval until completion
   */
  pollOrderUntilComplete: async (
    orderId: string,
    interval: number = 2000,
    maxAttempts: number = 30,
  ): Promise<TradingHistoryResponse> => {
    let attempts = 0

    while (attempts < maxAttempts) {
      try {
        const orderStatus = await apiClient.get<TradingHistoryResponse>(`/trading/poll/${orderId}`)
        const status = orderStatus.data.status

        // Return if order is in final state
        if (status === 'completed' || status === 'failed') {
          return orderStatus.data
        }

        // Wait before next poll
        if (attempts < maxAttempts - 1) {
          await new Promise((resolve) => setTimeout(resolve, interval))
        }
      } catch (error) {
        console.error(`Error polling order ${orderId}:`, error)
        throw error
      }

      attempts++
    }

    throw new Error(`Order ${orderId} did not complete within ${maxAttempts} polling attempts`)
  },
}
