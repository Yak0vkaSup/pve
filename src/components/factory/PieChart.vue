<template>
  <div class="chart-wrapper" :style="myStyles">
    <Doughnut v-if="loaded" :data="chartData" :options="chartOptions" />
  </div>
</template>

<script>
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, ArcElement)

export default {
  name: 'PieChart',
  components: { Doughnut },
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
    myStyles () {
      return {
        height: '300px',
        position: 'relative'
      }
    }
  },
  data() {
    return {
      loaded: true
    }
  }
}
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
}
</style>
