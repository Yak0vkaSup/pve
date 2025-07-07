<!-- src/components/ButtonControls.vue -->
<template>
  <div class="button-container">
    <button @click="graphStore.saveGraphToServer">Save</button>
    
    <!-- Strategy Management Section -->
    <div class="strategy-management">
      <select
        v-model="graphStore.selectedGraph"
        @focus="graphStore.fetchSavedGraphs"
        @change="handleGraphChange"
        class="select-saved-graph compact-dropdown"
      >
        <option disabled value="">Select strategy</option>
        <option v-for="graph in graphStore.savedGraphs" :key="graph.id" :value="graph.name">
          {{ graph.name }}
        </option>
      </select>
      
      <!-- Create New Strategy Button -->
      <button 
        @click="showCreateStrategyDialog = true" 
        class="create-strategy-btn"
        title="Create new empty strategy"
      >
        +
      </button>
      
      <!-- Duplicate Strategy Button -->
      <button 
        @click="showDuplicateDialog" 
        :disabled="!graphStore.selectedGraph"
        class="duplicate-strategy-btn"
        title="Duplicate selected strategy"
      >
        ⧉
      </button>
      
      <!-- Delete Strategy Button -->
      <button 
        @click="showDeleteConfirmation" 
        :disabled="!graphStore.selectedGraph"
        class="delete-strategy-btn"
        title="Delete selected strategy"
      >
        −
      </button>
    </div>

    <!-- Updated datetime inputs with seconds precision -->
    <input
      type="datetime-local"
      v-model="graphStore.startDate"
      class="input-datetime"
      placeholder="Start Date & Time"
      step="1"
    />
    <input
      type="datetime-local"
      v-model="graphStore.endDate"
      class="input-datetime"
      placeholder="End Date & Time"
      step="1"
    />

    <select v-model="graphStore.timeframe" class="select-timeframe compact-dropdown">
      <option value="1min">1 Min</option>
      <option value="3min">3 Min</option>
      <option value="5min">5 Min</option>
      <option value="15min">15 Min</option>
      <option value="30min">30 Min</option>
      <option value="1h">1h</option>
    </select>

    <select v-model="graphStore.symbol" class="select-symbol compact-dropdown">
      <option disabled value="">Symbol</option>
      <option v-for="symbol in graphStore.symbolOptions" :key="symbol" :value="symbol">
        {{ symbol }}
      </option>
    </select>

    <div class="button-with-tooltip">
      <button
        @click="async () => {
          await graphStore.saveGraphToServer();
          graphStore.compileGraph();
        }"
        :disabled="graphStore.compilationProgress.isCompiling"
      >
        {{ graphStore.compilationProgress.isCompiling ? 'Compiling...' : 'Compile' }}
      </button>
      
      <!-- Progress Tooltip -->
      <div v-if="graphStore.compilationProgress.isCompiling" class="progress-tooltip show">
        <div class="progress-bar-tooltip">
          <div 
            class="progress-fill-tooltip" 
            :style="{ width: graphStore.compilationProgress.progress + '%' }"
          ></div>
        </div>
        <div class="progress-text-tooltip">
          {{ graphStore.compilationProgress.progress }}% - {{ graphStore.compilationProgress.stage }}
        </div>
      </div>
    </div>

    <div class="button-with-tooltip">
      <button @click="graphStore.downloadGraph">Download</button>
    </div>
    
    <div class="button-with-tooltip">
      <button @click="triggerFileUpload">Upload</button>
    </div>
    <input type="file" ref="fileInput" @change="handleFileUpload" accept=".json" style="display: none" />

    <!-- Create Strategy Dialog -->
    <div v-if="showCreateStrategyDialog" class="modal-overlay" @click="closeCreateDialog">
      <div class="modal-content" @click.stop>
        <h3>Create New Strategy</h3>
        <input 
          v-model="newStrategyName" 
          placeholder="Enter strategy name" 
          class="modal-input"
          @keyup.enter="createNewStrategy"
          ref="strategyNameInput"
        />
        <div class="modal-buttons">
          <button @click="createNewStrategy" :disabled="!newStrategyName.trim()" class="modal-btn-primary">Create</button>
          <button @click="closeCreateDialog" class="modal-btn-secondary">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Duplicate Strategy Dialog -->
    <div v-if="showDuplicateStrategyDialog" class="modal-overlay" @click="closeDuplicateDialog">
      <div class="modal-content" @click.stop>
        <h3>Duplicate Strategy</h3>
        <input 
          v-model="duplicateStrategyName" 
          placeholder="Enter name for duplicated strategy" 
          class="modal-input"
          @keyup.enter="duplicateStrategy"
          ref="duplicateNameInput"
        />
        <div class="modal-buttons">
          <button @click="duplicateStrategy" :disabled="!duplicateStrategyName.trim()" class="modal-btn-primary">Duplicate</button>
          <button @click="closeDuplicateDialog" class="modal-btn-secondary">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <div v-if="showDeleteDialog" class="modal-overlay" @click="closeDeleteDialog">
      <div class="modal-content" @click.stop>
        <h3>Confirm Deletion</h3>
        <p>Are you sure you want to delete the strategy "<strong>{{ strategyToDelete?.name }}</strong>"?</p>
        <p class="warning-text">This action cannot be undone.</p>
        <div class="modal-buttons">
          <button @click="confirmDelete" class="modal-btn-danger">Delete</button>
          <button @click="closeDeleteDialog" class="modal-btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useGraphStore } from '../../stores/graph.ts'
import { onMounted, ref, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth.ts'
import '../../assets/inputs.css'

const graphStore = useGraphStore()
const fileInput = ref(null)
const authStore = useAuthStore()
const strategyNameInput = ref(null)
const duplicateNameInput = ref(null)

// Dialog state
const showCreateStrategyDialog = ref(false)
const showDuplicateStrategyDialog = ref(false)
const showDeleteDialog = ref(false)
const newStrategyName = ref('')
const duplicateStrategyName = ref('')
const strategyToDelete = ref(null)

onMounted(async () => {
  if (!authStore.isAuthenticated) {
    return
  }
  
  // Initialize default dates if not already set
  graphStore.initializeDates()
})

const handleGraphChange = () => {
  graphStore.loadGraphFromServer()
}

const triggerFileUpload = () => {
  fileInput.value.click()
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const graphData = JSON.parse(e.target.result)
        graphStore.loadGraphFromFile(graphData, file.name)
      } catch (error) {
        console.error('Error parsing uploaded graph JSON')
      }
    }
    reader.readAsText(file)
  }
}

const closeCreateDialog = () => {
  showCreateStrategyDialog.value = false
  newStrategyName.value = ''
}

const createNewStrategy = async () => {
  if (!newStrategyName.value.trim()) return
  
  const success = await graphStore.createEmptyStrategy(newStrategyName.value.trim())
  if (success) {
    closeCreateDialog()
  }
}

const showDuplicateDialog = () => {
  if (!graphStore.selectedGraph) return
  
  const selectedStrategy = graphStore.savedGraphs.find(g => g.name === graphStore.selectedGraph)
  if (selectedStrategy) {
    duplicateStrategyName.value = selectedStrategy.name + ' Copy'
    showDuplicateStrategyDialog.value = true
    nextTick(() => {
      if (duplicateNameInput.value) {
        duplicateNameInput.value.focus()
        duplicateNameInput.value.select()
      }
    })
  }
}

const closeDuplicateDialog = () => {
  showDuplicateStrategyDialog.value = false
  duplicateStrategyName.value = ''
}

const duplicateStrategy = async () => {
  if (!duplicateStrategyName.value.trim() || !graphStore.selectedGraph) return
  
  const success = await graphStore.duplicateStrategy(graphStore.selectedGraph, duplicateStrategyName.value.trim())
  if (success) {
    closeDuplicateDialog()
  }
}

const showDeleteConfirmation = () => {
  if (!graphStore.selectedGraph) return
  
  const selectedStrategy = graphStore.savedGraphs.find(g => g.name === graphStore.selectedGraph)
  if (selectedStrategy) {
    strategyToDelete.value = selectedStrategy
    showDeleteDialog.value = true
  }
}

const closeDeleteDialog = () => {
  showDeleteDialog.value = false
  strategyToDelete.value = null
}

const confirmDelete = async () => {
  if (strategyToDelete.value) {
    const success = await graphStore.deleteStrategyById(strategyToDelete.value.id)
    if (success) {
      closeDeleteDialog()
    }
  }
}

// Focus input when dialog opens
const openCreateDialog = async () => {
  showCreateStrategyDialog.value = true
  await nextTick()
  if (strategyNameInput.value) {
    strategyNameInput.value.focus()
  }
}
</script>

<style scoped>
.button-container{
  margin-top: 0.5vh;
  margin-bottom: 0.5vh;
  gap: 1vh;
}

.strategy-management {
  display: flex;
  align-items: center;
  gap: 5px;
}

.create-strategy-btn {
  width: 40px; /* Square */
  height: 40px; /* Square */
  padding: 10px 20px; /* Match inputs.css */
  background-color: #222222; /* Match inputs.css background */
  color: #28a745; /* Green text */
  border: none;
  border-radius: 5px; /* Match inputs.css */
  cursor: pointer;
  transition: background-color 0.3s ease; /* Match inputs.css */
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.create-strategy-btn:hover {
  background-color: #353535; /* Match inputs.css hover */
}

.delete-strategy-btn {
  width: 40px; /* Square */
  height: 40px; /* Square */
  padding: 10px 20px; /* Match inputs.css */
  background-color: #222222; /* Match inputs.css background */
  color: #dc3545; /* Red text */
  border: none;
  border-radius: 5px; /* Match inputs.css */
  cursor: pointer;
  transition: background-color 0.3s ease; /* Match inputs.css */
  font-size: 18px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-strategy-btn:hover:not(:disabled) {
  background-color: #353535; /* Match inputs.css hover */
}

.delete-strategy-btn:disabled {
  background-color: #222222;
  color: #6c757d; /* Gray text when disabled */
  cursor: not-allowed;
  opacity: 0.6;
}

/* Ensure ALL elements have the same height */
.select-saved-graph,
.input-datetime,
.select-timeframe,
.select-symbol,
.button-with-tooltip button {
  height: 40px !important; /* Force same height as strategy buttons */
  padding: 10px 20px !important; /* Force same padding */
  background-color: #222222 !important;
  color: #fff !important;
  border: none !important;
  border-radius: 5px !important;
  transition: background-color 0.3s ease !important;
  box-sizing: border-box !important; /* Ensure padding doesn't add to height */
}

.select-saved-graph:hover,
.input-datetime:hover,
.select-timeframe:hover,
.select-symbol:hover,
.button-with-tooltip button:hover:not(:disabled),
.select-saved-graph:focus,
.input-datetime:focus,
.select-timeframe:focus,
.select-symbol:focus {
  background-color: #353535 !important;
  outline: none !important;
}

/* Compact dropdowns for better fit */
.compact-dropdown {
  width: 120px !important; /* Smaller width to fit interface */
}

.duplicate-strategy-btn {
  width: 40px; /* Square */
  height: 40px; /* Square */
  padding: 10px 20px; /* Match inputs.css */
  background-color: #222222; /* Match inputs.css background */
  color: #007bff; /* Blue text for duplicate */
  border: none;
  border-radius: 5px; /* Match inputs.css */
  cursor: pointer;
  transition: background-color 0.3s ease; /* Match inputs.css */
  font-size: 16px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.duplicate-strategy-btn:hover:not(:disabled) {
  background-color: #353535; /* Match inputs.css hover */
}

.duplicate-strategy-btn:disabled {
  background-color: #222222;
  color: #6c757d; /* Gray text when disabled */
  cursor: not-allowed;
  opacity: 0.6;
}

.button-with-tooltip {
  position: relative;
  display: inline-block;
}

.progress-tooltip {
  position: absolute;
  top: -80px;
  left: 50%;
  transform: translateX(-50%);
  background-color: #222222;
  border: 1px solid #353535;
  border-radius: 5px;
  padding: 12px 16px;
  min-width: 250px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease, transform 0.3s ease;
  transform: translateX(-50%) translateY(10px);
}

.progress-tooltip.show {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(0);
}

.progress-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #222222;
}

.progress-bar-tooltip {
  width: 100%;
  height: 8px;
  background-color: #353535;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill-tooltip {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #45a049);
  transition: width 0.5s ease;
  border-radius: 4px;
  box-shadow: 0 0 8px rgba(76, 175, 80, 0.3);
}

.progress-text-tooltip {
  font-size: 12px;
  color: #fff;
  text-align: center;
  font-weight: 500;
  line-height: 1.2;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal Styles - Aligned with inputs.css */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.modal-content {
  background-color: #222222; /* Match inputs.css background */
  border: 1px solid #353535; /* Subtle border */
  border-radius: 5px; /* Match inputs.css border-radius */
  padding: 20px;
  min-width: 400px;
  max-width: 500px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.modal-content h3 {
  margin: 0 0 16px 0;
  color: #fff; /* Match inputs.css text color */
  font-size: 18px;
  font-weight: 600;
}

.modal-content p {
  margin: 0 0 16px 0;
  color: #fff; /* Match inputs.css text color */
  line-height: 1.5;
}

.warning-text {
  color: #ffc107 !important;
  font-weight: 500;
  font-size: 14px;
}

.modal-input {
  width: 100%;
  padding: 10px 20px; /* Match inputs.css padding */
  background-color: #222222; /* Match inputs.css background */
  color: #fff; /* Match inputs.css text color */
  border: none;
  border-radius: 5px; /* Match inputs.css border-radius */
  font-size: 14px;
  margin-bottom: 20px;
  transition: background-color 0.3s ease; /* Match inputs.css transition */
}

.modal-input:hover,
.modal-input:focus {
  background-color: #353535; /* Match inputs.css hover color */
  outline: none;
}

.modal-input::placeholder {
  color: white; /* Match inputs.css placeholder color */
}

.modal-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

/* Modal button styles matching inputs.css */
.modal-btn-primary,
.modal-btn-secondary,
.modal-btn-danger {
  padding: 10px 20px; /* Match inputs.css padding */
  background-color: #222222; /* Match inputs.css background */
  color: #fff; /* Match inputs.css text color */
  border: none;
  border-radius: 5px; /* Match inputs.css border-radius */
  cursor: pointer;
  transition: background-color 0.3s ease; /* Match inputs.css transition */
  font-size: 14px;
  font-weight: 500;
}

.modal-btn-primary {
  background-color: #28a745;
}

.modal-btn-primary:hover:not(:disabled) {
  background-color: #218838;
}

.modal-btn-primary:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
  opacity: 0.6;
}

.modal-btn-secondary:hover {
  background-color: #353535; /* Match inputs.css hover color */
}

.modal-btn-danger {
  background-color: #dc3545;
}

.modal-btn-danger:hover {
  background-color: #c82333;
}
</style>
