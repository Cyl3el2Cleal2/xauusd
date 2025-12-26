/**
 * Format currency using Thai Baht (THB) formatting
 * @param value - The numeric value to format
 * @returns Formatted Thai Baht string
 */
export const formatThaiCurrency = (value: number): string => {
  return new Intl.NumberFormat('th-TH', {
    style: 'currency',
    currency: 'THB',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

/**
 * Format amount for gold ounces
 * @param value - The numeric value to format
 * @returns Formatted amount string with "oz" suffix
 */
export const formatGoldAmount = (value: number): string => {
  return `${value.toFixed(1)} oz`
}

/**
 * Format timestamp to a readable date format
 * @param timestamp - ISO timestamp string
 * @returns Formatted date string
 */
export const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    year: 'numeric',
  })
}

/**
 * Get CSS class for transaction type styling
 * @param type - Transaction type ('buy' or 'sell')
 * @returns CSS class string
 */
export const getTransactionTypeClass = (type: string): string => {
  return type === 'buy' ? 'text-green-600' : 'text-red-600'
}

/**
 * Get icon for transaction type
 * @param type - Transaction type ('buy' or 'sell')
 * @returns Icon string (↑ for buy, ↓ for sell)
 */
export const getTransactionIcon = (type: string): string => {
  return type === 'buy' ? '↑' : '↓'
}

/**
 * Get CSS class for status badge
 * @param status - Transaction status
 * @returns CSS class string for status badge
 */
export const getStatusBadgeClass = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

/**
 * Transaction interface definition
 */
export interface Transaction {
  id: string
  type: 'buy' | 'sell'
  amount: number
  price: number
  total: number
  timestamp: string
  status: 'completed' | 'pending' | 'failed'
  fee: number
}