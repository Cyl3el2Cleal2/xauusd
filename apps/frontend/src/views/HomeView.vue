<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import VueApexCharts from 'vue3-apexcharts' // Ensure this is installed
import TheWelcome from '../components/TheWelcome.vue'

// 1. Define Template Ref for the chart component
const chart = ref<any>(null)

// 2. State & Constants
const XAXISRANGE = 777600000 // Example range value
let lastDate = 0
let data: any[] = []

// 3. Reactive Series (ApexCharts watches this)
const series = ref([{
  data: data.slice()
}])

// 4. Chart Options (Can stay as a plain object)
const chartOptions = {
  chart: {
    id: 'realtime',
    height: 350,
    type: 'line',
    animations: {
      enabled: true,
      easing: 'linear',
      dynamicAnimation: { speed: 1000 }
    },
    toolbar: { show: false },
    zoom: { enabled: false }
  },
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth' },
  title: { text: 'Realtime Gold Strategy', align: 'left' },
  xaxis: {
    type: 'datetime',
    range: XAXISRANGE,
  },
  yaxis: { max: 100 },
  legend: { show: false },
}

// Mock functions (replace with your actual logic)
const getNewSeries = (baseval: number, yrange: {min: number, max: number}) => {
  const newDate = baseval + 86400000
  lastDate = newDate
  data.push({
    x: newDate,
    y: Math.floor(Math.random() * (yrange.max - yrange.min + 1)) + yrange.min
  })
}

const resetData = () => {
  data = data.slice(data.length - 10, data.length)
}

// 5. Lifecycle Hooks
let interval1: any, interval2: any

onMounted(() => {
  // Update loop
  interval1 = window.setInterval(() => {
    getNewSeries(lastDate, { min: 10, max: 90 })
    
    // Accessing the chart instance via ref
    if (chart.value) {
      chart.value.updateSeries([{
        data: data
      }])
    }
  }, 1000)

  // Memory leak prevention loop
  interval2 = window.setInterval(() => {
    resetData()
    if (chart.value) {
      chart.value.updateSeries([{ data }], false, true)
    }
  }, 60000)
})

// Clean up intervals when component is destroyed
onUnmounted(() => {
  clearInterval(interval1)
  clearInterval(interval2)
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