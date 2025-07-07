<!-- src/components/factory/InlineTabs.vue -->
<template>
  <div class="inline-tabs-wrapper">
    <div class="tab-header">
      <button :class="{ active: activeTab === 'nodes' }" @click="activeTab = 'nodes'">
        Nodes
      </button>
      <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
        Logs
      </button>
      <button :class="{ active: activeTab === 'analyze' }" @click="activeTab = 'analyze'">
        Analyze
      </button>
    </div>
    <div class="tab-content">
      <component :is="activeComponent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Nodes from './Nodes.vue'
import Logs from './Logs.vue'
import Analyze from './Analyze.vue'

const activeTab = ref('nodes')

const activeComponent = computed(() => {
  if (activeTab.value === 'logs') return Logs
  if (activeTab.value === 'analyze') return Analyze
  return Nodes
})
</script>

<style scoped>
.inline-tabs-wrapper {

  background: var(--color-background, #181818);
}

.tab-header {
  display: flex;
  margin-bottom: 0.5vh;
}

.tab-header button {
  flex: 1;
  padding: 5px; /* Adjusted padding */
  border: none;
  background: var(--color-background, #181818);
  color: var(--color-heading, #ffffff);
  cursor: pointer;
  transition: background 0.2s ease;
  font-size: 12px; /* Slightly smaller font */
}

.tab-header button:hover {
  background: var(--color-background-soft, #222222);
}

.tab-header button.active {
  background: var(--color-background-soft, #222222);
}

.tab-content {
  background: var(--color-background, #222222);
}

</style>
