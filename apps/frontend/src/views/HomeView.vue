<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { usePrice } from '@/apis/price'
import { useTradingControlStore } from '@/stores/trading-control'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import UserModal from '@/components/UserModal.vue'
import Order from '@/components/Order.vue'

// Register necessary ECharts components
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
])

interface ChartData {
  x: number
  y: number
}

const { gold96Price, goldSpotPrice, streamSymbol } = usePrice()
const tradingControlStore = useTradingControlStore()

// Store chart data
const chartData = ref<ChartData[]>([])
const buyData = ref<ChartData[]>([])
const sellData = ref<ChartData[]>([])
const maxDataPoints = 200

// Get trading status for each symbol
const getTradingStatus = (symbol: string) => {
  const control = tradingControlStore.getControlBySymbol(symbol)
  return control ? control.status : 'online'
}

// Store last known prices to maintain continuity
let lastSpotPrice: number | null = null
let lastBuyPrice: number | null = null
let lastSellPrice: number | null = null

// ECharts configuration
const option = ref({
  title: {
    text: 'Gold Price Real-Time Chart',
    left: 'center',
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross',
    },
    formatter: function (params: any) {
      let result = 'Time: ' + new Date(params[0].axisValue).toLocaleTimeString() + '<br/>'
      params.forEach((param: any) => {
        result += param.marker + ' ' + param.seriesName + ': ' + param.value[1].toFixed(2) + '<br/>'
      })
      return result
    },
  },
  legend: {
    data: ['Gold Spot', 'Gold96 Buy', 'Gold96 Sell'],
    top: 30,
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true,
  },
  xAxis: {
    type: 'time',
    splitLine: {
      show: false,
    },
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      formatter: (value: number) => value.toFixed(2),
    },
    // Scales the axis to fit your data exactly
    min: 'dataMin',
    max: 'dataMax',
    // Adds a little "padding" so the line doesn't touch the top/bottom edges
    boundaryGap: ['20%', '20%'],
    splitLine: {
      show: false,
      lineStyle: {
        color: '#f0f0f0',
      },
    },
  },
  series: [
    {
      name: 'Gold Spot',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#FFD700', // Gold
      },
      data: [] as [number, number][],
    },
    {
      name: 'Gold96 Buy',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#00FF00', // Green
      },
      data: [] as [number, number][],
    },
    {
      name: 'Gold96 Sell',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#FF0000', // Red
      },
      data: [] as [number, number][],
    },
  ],
  animationDuration: 300,
})

// Watch for price updates and update chart data
watch(goldSpotPrice, (val) => {
  const status = getTradingStatus('spot')

  let priceToUse: number
  if (status === 'stop') {
    priceToUse = 0
  } else if (status === 'pause') {
    // Don't update price, keep last known price
    return
  } else {
    // Online - use actual price
    if (!val || !val.price) return
    priceToUse = parseFloat(val.price.toString().replace(/,/g, ''))
  }

  const timestamp = Date.now()
  const newPrice: ChartData = {
    x: timestamp,
    y: priceToUse,
  }

  chartData.value.push(newPrice)
  lastSpotPrice = priceToUse

  // Update ECharts series data
  option.value.series[0]?.data?.push([timestamp, priceToUse])

  // Limit data array size
  if (chartData.value.length > maxDataPoints) {
    chartData.value.shift()
    option.value.series[0]?.data?.shift()
  }
})

watch(gold96Price, (val) => {
  const status = getTradingStatus('gold96')

  let buyPriceToUse: number
  let sellPriceToUse: number

  if (status === 'stop') {
    buyPriceToUse = 0
    sellPriceToUse = 0
  } else if (status === 'pause') {
    // Don't update prices, keep last known prices
    return
  } else {
    // Online - use actual prices
    if (!val || !val.buy_price) return
    buyPriceToUse = parseFloat(val.buy_price)
    sellPriceToUse = parseFloat(val.sell_price)
  }

  console.log(val)

  const timestamp = Date.now()

  const newBuyPrice: ChartData = {
    x: timestamp,
    y: buyPriceToUse,
  }
  const newSellPrice: ChartData = {
    x: timestamp,
    y: sellPriceToUse,
  }

  buyData.value.push(newBuyPrice)
  sellData.value.push(newSellPrice)
  lastBuyPrice = buyPriceToUse
  lastSellPrice = sellPriceToUse

  // Update ECharts series data
  option.value.series[1]?.data?.push([timestamp, buyPriceToUse])
  option.value.series[2]?.data?.push([timestamp, sellPriceToUse])

  // Limit data arrays to prevent memory lag
  if (buyData.value.length > maxDataPoints) {
    buyData.value.shift()
    option.value.series[1]?.data?.shift()
  }
  if (sellData.value.length > maxDataPoints) {
    sellData.value.shift()
    option.value.series[2]?.data?.shift()
  }
})

// Continuous data points to maintain line continuity
let updateInterval: number

onMounted(() => {
  streamSymbol(gold96Price, 'gold96')
  streamSymbol(goldSpotPrice, 'spot')

  // Add continuous data points to maintain line continuity
  updateInterval = window.setInterval(() => {
    const timestamp = Date.now()

    const spotStatus = getTradingStatus('spot')
    const gold96Status = getTradingStatus('gold96')

    // Always add data points to keep the graph moving every second
    // Use last known prices for pause, 0 for stop, or maintain for online

    // Handle spot price
    if (lastSpotPrice !== null) {
      const lastDataPoint = chartData.value[chartData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        let priceToUse = lastSpotPrice
        if (spotStatus === 'stop') {
          priceToUse = 0
        }

        chartData.value.push({ x: timestamp, y: priceToUse })
        option.value.series[0]?.data?.push([timestamp, priceToUse])

        if (chartData.value.length > maxDataPoints) {
          chartData.value.shift()
          option.value.series[0]?.data?.shift()
        }
      }
    }

    // Handle gold96 buy price
    if (lastBuyPrice !== null) {
      const lastDataPoint = buyData.value[buyData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        let priceToUse = lastBuyPrice
        if (gold96Status === 'stop') {
          priceToUse = 0
        }

        buyData.value.push({ x: timestamp, y: priceToUse })
        option.value.series[1]?.data?.push([timestamp, priceToUse])

        if (buyData.value.length > maxDataPoints) {
          buyData.value.shift()
          option.value.series[1]?.data?.shift()
        }
      }
    }

    // Handle gold96 sell price
    if (lastSellPrice !== null) {
      const lastDataPoint = sellData.value[sellData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        let priceToUse = lastSellPrice
        if (gold96Status === 'stop') {
          priceToUse = 0
        }

        sellData.value.push({ x: timestamp, y: priceToUse })
        option.value.series[2]?.data?.push([timestamp, priceToUse])

        if (sellData.value.length > maxDataPoints) {
          sellData.value.shift()
          option.value.series[2]?.data?.shift()
        }
      }
    }
  }, 500)
})

onUnmounted(() => {
  clearInterval(updateInterval)
})
</script>

<template>
  <main>
    <div class="chart-container">
      <v-chart class="chart" :option="option" autoresize />
    </div>
    <Order />
    <UserModal />
  </main>
</template>

<style scoped>
main {
  padding-top: 80px; /* Account for fixed navbar height */
  min-height: 100vh;
  background-color: #f8fafc; /* Light background to ensure navbar is visible */
}

.chart-container {
  width: 100%;
  height: 500px;
  padding: 20px;
}

.chart {
  width: 100%;
  height: 100%;
}

/* Mobile responsive styles */
@media (max-width: 768px) {
  main {
    padding: 80px 0 0 0; /* Only top padding for mobile */
  }

  .chart-container {
    padding: 0;
    height: 400px;
  }
}

@media (max-width: 480px) {
  .chart-container {
    height: 350px;
  }
}
</style>
