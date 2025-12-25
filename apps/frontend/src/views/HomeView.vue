<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { usePrice } from '@/apis/price'
import type ApexCharts from 'apexcharts'

interface ChartData {
  x: number
  y: number
}

const chart = ref<ApexCharts | null>(null)
const { gold96Price, goldSpotPrice, streamSymbol } = usePrice()

// Store chart data
const chartData = ref<ChartData[]>([])
const XAXISRANGE = 300000

// Watch for price updates and update chart data
watch(goldSpotPrice, (val) => {
  if (!val || !val.price) return

  const cleanPrice = parseFloat(val.price.toString().replace(/,/g, ''))

  const newPrice: ChartData = {
    x: val.time, // Ensure this is a timestamp in ms
    y: cleanPrice,
  }
  console.log('New price data:', newPrice)
  chartData.value.push(newPrice)

  // Limit data array size to prevent memory lag
  if (chartData.value.length > 200) {
    chartData.value.shift()
  }
})

watch(gold96Price, (val) => {
  if (!val) return
  const buyPrice = parseFloat(val.buy_price.toString())
  const sellPrice = parseFloat(val.sell_price.toString())
})

// Chart configuration
const chartOptions = {
  chart: {
    id: 'realtime',
    height: 350,
    type: 'line',
    animations: {
      enabled: true,
      easing: 'linear',
      dynamicAnimation: { speed: 1000 },
    },
    toolbar: { show: false },
    zoom: { enabled: true },
  },
  stroke: { curve: 'smooth', width: 3 },
  xaxis: {
    type: 'datetime',
    range: XAXISRANGE,
  },
  yaxis: {
    labels: {
      formatter: (val: number) => val.toFixed(2),
    },
    forceNiceScale: true,
  },
}

// Use reactive series that's connected to chartData
const series = ref([
  {
    name: 'Gold Spot Price',
    data: chartData.value,
  },
])

let interval1: number

onMounted(() => {
  streamSymbol(gold96Price, 'gold96')
  streamSymbol(goldSpotPrice, 'spot')

  // Update chart periodically with latest data
  interval1 = window.setInterval(() => {
    if (chart.value && chartData.value.length > 0) {
      chart.value.updateSeries([
        {
          data: [...chartData.value], // Pass a shallow copy
        },
      ])
    }
  }, 1000)
})

onUnmounted(() => {
  clearInterval(interval1)
})
</script>

<template>
  <main>
    <div id="chart">
      <apexchart
        type="line"
        height="350"
        ref="chart"
        :options="chartOptions"
        :series="series"
      ></apexchart>
    </div>
  </main>
</template>
