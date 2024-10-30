<!-- src/components/ButtonControls.vue -->
<template>
  <div class="button-container">
    <input v-model="graphStore.graphName" placeholder="Enter graph name" class="input-graph-name" />

    <button @click="graphStore.saveGraphToServer">Save</button>
    <button @click="graphStore.deleteGraphToServer">Delete</button>

    <select
      v-model="graphStore.selectedGraph"
      @focus="graphStore.fetchSavedGraphs"
      @change="handleGraphChange"
      class="select-saved-graph"
    >
      <option disabled value="">Select a saved graph</option>
      <option v-for="graph in graphStore.savedGraphs" :key="graph.id" :value="graph.name">
        {{ graph.name }}
      </option>
    </select>

    <input type="date" v-model="graphStore.savedGraphs.startDate" class="input-date" placeholder="Start Date" />
    <input type="date" v-model="graphStore.savedGraphs.endDate" class="input-date" placeholder="End Date" />

<!--    <select v-model="graphStore.savedGraphs.timeframe" class="select-timeframe">-->
<!--      <option value="1min">1 Minute</option>-->
<!--      <option value="5min">5 Minutes</option>-->
<!--      <option value="15min">15 Minutes</option>-->
<!--      &lt;!&ndash; Add more options as needed &ndash;&gt;-->
<!--    </select>-->

    <select v-model="graphStore.savedGraphs.symbol" class="select-symbol">
      <option disabled value="">Select a symbol</option>
      <option v-for="symbol in graphStore.savedGraphs.symbolOptions" :key="symbol" :value="symbol">
        {{ symbol }}
      </option>
    </select>

    <button @click="graphStore.compileGraph">Compile</button>
  </div>
</template>

<script setup>
import { useGraphStore } from '../stores/graph.ts'

const graphStore = useGraphStore()

const handleGraphChange = () => {
  graphStore.loadGraphFromServer()
  graphStore.graphName = graphStore.selectedGraph
}
</script>

<style scoped>
.button-container{
  margin-top: 1vh;
  margin-bottom: 1vh;
}

</style>
