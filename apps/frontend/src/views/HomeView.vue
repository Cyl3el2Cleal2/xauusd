<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { usePrice } from '@/apis/price'
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

// Store chart data
const chartData = ref<ChartData[]>([])
const buyData = ref<ChartData[]>([])
const sellData = ref<ChartData[]>([])
const maxDataPoints = 200

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
    data: ['Gold Spot Price', 'Buy Price', 'Sell Price'],
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
    boundaryGap: ['10%', '10%'],
    splitLine: {
      show: false,
      lineStyle: {
        color: '#f0f0f0',
      },
    },
  },
  series: [
    {
      name: 'Gold Spot Price',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#FFD700', // Gold
      },
      data: [],
    },
    {
      name: 'Buy Price',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#00FF00', // Green
      },
      data: [],
    },
    {
      name: 'Sell Price',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: {
        width: 2,
        color: '#FF0000', // Red
      },
      data: [],
    },
  ],
  animationDuration: 300,
})

// Watch for price updates and update chart data
watch(goldSpotPrice, (val) => {
  if (!val || !val.price) return

  const cleanPrice = parseFloat(val.price.toString().replace(/,/g, ''))
  const timestamp = Date.now()

  const newPrice: ChartData = {
    x: timestamp,
    y: cleanPrice,
  }

  chartData.value.push(newPrice)
  lastSpotPrice = cleanPrice

  // Update ECharts series data
  option.value.series[0].data.push([timestamp, cleanPrice])

  // Limit data array size
  if (chartData.value.length > maxDataPoints) {
    chartData.value.shift()
    option.value.series[0].data.shift()
  }
})

watch(gold96Price, (val) => {
  if (!val) return

  const buyPrice = parseFloat(val.buy_price.toString().replace(/,/g, ''))
  const sellPrice = parseFloat(val.sell_price.toString().replace(/,/g, ''))
  const timestamp = Date.now()

  const newBuyPrice: ChartData = {
    x: timestamp,
    y: buyPrice,
  }
  const newSellPrice: ChartData = {
    x: timestamp,
    y: sellPrice,
  }

  buyData.value.push(newBuyPrice)
  sellData.value.push(newSellPrice)
  lastBuyPrice = buyPrice
  lastSellPrice = sellPrice

  // Update ECharts series data
  option.value.series[1].data.push([timestamp, buyPrice])
  option.value.series[2].data.push([timestamp, sellPrice])

  // Limit data arrays to prevent memory lag
  if (buyData.value.length > maxDataPoints) {
    buyData.value.shift()
    option.value.series[1].data.shift()
  }
  if (sellData.value.length > maxDataPoints) {
    sellData.value.shift()
    option.value.series[2].data.shift()
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
    let hasNewData = false

    // Add current timestamp with last known price to maintain continuity
    if (lastSpotPrice !== null) {
      const lastDataPoint = chartData.value[chartData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        chartData.value.push({ x: timestamp, y: lastSpotPrice })
        option.value.series[0].data.push([timestamp, lastSpotPrice])

        if (chartData.value.length > maxDataPoints) {
          chartData.value.shift()
          option.value.series[0].data.shift()
        }
        hasNewData = true
      }
    }

    if (lastBuyPrice !== null) {
      const lastDataPoint = buyData.value[buyData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        buyData.value.push({ x: timestamp, y: lastBuyPrice })
        option.value.series[1].data.push([timestamp, lastBuyPrice])

        if (buyData.value.length > maxDataPoints) {
          buyData.value.shift()
          option.value.series[1].data.shift()
        }
        hasNewData = true
      }
    }

    if (lastSellPrice !== null) {
      const lastDataPoint = sellData.value[sellData.value.length - 1]
      if (!lastDataPoint || timestamp - lastDataPoint.x >= 1000) {
        sellData.value.push({ x: timestamp, y: lastSellPrice })
        option.value.series[2].data.push([timestamp, lastSellPrice])

        if (sellData.value.length > maxDataPoints) {
          sellData.value.shift()
          option.value.series[2].data.shift()
        }
        hasNewData = true
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
.chart-container {
  width: 100%;
  height: 500px;
  padding: 20px;
}

.chart {
  width: 100%;
  height: 100%;
}
</style>
