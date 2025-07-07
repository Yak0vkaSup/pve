<template>
  <div class="chart-wrapper" :style="myStyles">
    <Bar v-if="loaded" :data="chartData" :options="chartOptions" />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

export default {
  name: 'LineChart', // You can also use a Line chart if preferred
  components: { Bar },
  props: {
    chartData: {
      type: Object,
      required: true
    },
    chartOptions: {
      type: Object,
      default: () => ({})
    }
  },
  computed: {
    myStyles() {
      return {
        height: '300px',
        position: 'relative'
      }
    }
  },
  data() {
    return { loaded: true }
  }
}
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
}
</style>
