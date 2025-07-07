// src/stores/graphStore.ts

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Ref } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import 'litegraph.js/css/litegraph.css'
import axios from 'axios'
import { toast } from 'vue3-toastify'

// Import your custom vpl
import '../components/custom_nodes/get/open.js'
import '../components/custom_nodes/get/high.js'
import '../components/custom_nodes/get/low.js'
import '../components/custom_nodes/get/close.js'
import '../components/custom_nodes/get/volume.js'
//import '../components/custom_nodes/get/last_value.js'

import '../components/custom_nodes/set/float.js'
import '../components/custom_nodes/set/integer.js'
import '../components/custom_nodes/set/string.js'
import '../components/custom_nodes/set/bool.js'

import '../components/custom_nodes/tools/add_signal.js'
import '../components/custom_nodes/tools/add_indicator.js'
//import '../components/custom_nodes/tools/get_column.js'
//import '../components/custom_nodes/tools/get_condition.js'

import '../components/custom_nodes/math/multiply_float.js'
import '../components/custom_nodes/math/divide_float.js'
import '../components/custom_nodes/math/add_float.js'
import '../components/custom_nodes/math/highest.js'
import '../components/custom_nodes/math/lowest.js'
import '../components/custom_nodes/math/subtract_float.js'
import '../components/custom_nodes/math/clip_float.js'

import '../components/custom_nodes/logic/_if.js'
import '../components/custom_nodes/logic/_and.js'
import '../components/custom_nodes/logic/_or.js'
import '../components/custom_nodes/logic/_not.js'

import '../components/custom_nodes/compare/cross_over.js'
import '../components/custom_nodes/compare/cross_under.js'
import '../components/custom_nodes/compare/equal.js'
import '../components/custom_nodes/compare/smaller.js'
import '../components/custom_nodes/compare/greater.js'

import '../components/custom_nodes/indicators/MaNode.js'
import '../components/custom_nodes/indicators/BollingerNode.js'
import '../components/custom_nodes/indicators/Supertrend.js'
import '../components/custom_nodes/indicators/RSINode.js'

import '../components/custom_nodes/telegram/send_message.js'
import '../components/custom_nodes/trade/create_order.js'
import '../components/custom_nodes/trade/create_conditional_order.js'

import '../components/custom_nodes/trade/get_order.js'
import '../components/custom_nodes/tools/is_none.js'
import '../components/custom_nodes/trade/get_last_order.js'
import '../components/custom_nodes/trade/save_order.js'
import '../components/custom_nodes/trade/cancel_order.js'
import '../components/custom_nodes/trade/cancel_all_orders.js'
import '../components/custom_nodes/trade/modify_order.js'

//import '../components/custom_nodes/trade/get_long_position.js'
//import '../components/custom_nodes/trade/get_short_position.js'
import '../components/custom_nodes/trade/get_position.js'

//import '../components/custom_nodes/backtest/simple_backtest.js'
//import '../components/custom_nodes/backtest/advanced_backtest.js'

// Set the base URL dynamically based on the environment variable.
const baseURL = import.meta.env.VITE_APP_ENV === 'dev'
  ? 'http://localhost:5001'
  : 'https://pve.finance'

const pve = { position: toast.POSITION.BOTTOM_RIGHT }

interface BybitTickersResponse {
  retCode: number
  retMsg: string
  result: {
    list: Ticker[]
  }
}

interface Ticker {
  symbol: string
  turnover24h: string
}

interface GraphData {
  id: number
  name: string
  modified_at: string
}

interface InternalApiResponse<T> {
  status: string;
  message?: string;
  graphs?: T
  graph_data?: T;
  start_date?: string;
  end_date?: string;
  symbol?: string;
  timeframe?: string;
}

export const useGraphStore = defineStore('graph', () => {
  // State Variables with Proper Types
  const graph: Ref<LGraph | null> = ref(null)
  const graphCanvas: Ref<LGraphCanvas | null> = ref(null)
  const graphName: Ref<string> = ref('')
  const savedGraphs: Ref<GraphData[]> = ref([])
  const selectedGraph: Ref<string> = ref('')
  const symbolOptions: Ref<string[]> = ref(['BTCUSDT', 'ETHUSDT', 'BNBUSDT'])
  const startDate: Ref<string> = ref('')
  const endDate: Ref<string> = ref('')

  // Initialize default dates when the store is created
  const initializeDates = (): void => {
    if (!startDate.value || !endDate.value) {
      setDefaultDates()
    }
  }
  const timeframe: Ref<string> = ref('1min')
  const symbol: Ref<string> = ref('')

  /**
   * Initializes the graph and canvas.
   */
  const initializeGraph = (canvasElement: HTMLCanvasElement): void => {
    const customLinkTypeColors: Record<string, string>  = {
        integer: "#d2ffb0",
        string: "#f3b0ff",
        bool: "#F77",
        float: "#b0e0ff",
        object: "#fffdb0",
        exec: "#dff4fb",
    };

    graph.value = new LGraph()
    graphCanvas.value = new LGraphCanvas(canvasElement, graph.value)

    if (graphCanvas.value) {
      (graphCanvas.value as any).default_connection_color_byType = customLinkTypeColors;
      (graphCanvas.value as any).default_connection_color_byTypeOff = customLinkTypeColors;
    }
    Object.assign(LGraphCanvas.link_type_colors, customLinkTypeColors);

    graph.value.start()
  }

  /**
   * Resizes the canvas to fit its parent container.
   */
  const resizeCanvas = (): void => {
    if (graphCanvas.value && graph.value) {
      const canvasElement = graphCanvas.value.canvas
      const parentElement = canvasElement.parentElement

      if (parentElement) {
        const style = getComputedStyle(parentElement)
        const width =
          parentElement.clientWidth -
          parseFloat(style.paddingLeft) -
          parseFloat(style.paddingRight)
        const height =
          parentElement.clientHeight -
          parseFloat(style.paddingTop) -
          parseFloat(style.paddingBottom)

        // Set the canvas's width and height attributes to match the display size
        canvasElement.width = width
        canvasElement.height = height
      }

      // Inform LiteGraphCanvas about the size change
      graphCanvas.value.resize()
    }
  }

  /**
   * Fetches symbols with turnover greater than the specified amount.
   */
  const getSymbolsByTurnover = async (turnover: number): Promise<string[]> => {
    try {
      const response = await axios.get<BybitTickersResponse>(
        'https://api.bybit.com/v5/market/tickers',
        { params: { category: 'linear' } }
      )

      if (response.data.retCode !== 0) {
        toast.error('Failed to get tickers info', pve)
        return []
      }

      const tickers: Ticker[] = response.data.result.list

      const filteredSymbols = tickers
        .filter((ticker: Ticker) => parseFloat(ticker.turnover24h) > turnover)
        .map((ticker: Ticker) => ticker.symbol)

      return filteredSymbols
    } catch (error) {
      toast.error('Error fetching symbols', pve)
      return []
    }
  }

  /**
   * Populates the symbol dropdown with fetched symbols.
   */
  const populateSymbolDropdown = async (): Promise<void> => {
    const symbols = await getSymbolsByTurnover(50000000)
    symbolOptions.value =
      symbols.length > 0 ? symbols : ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
  }

  /**
   * Fetches saved graphs from the server without auto-loading.
   */
  const fetchSavedGraphsList = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return
    }

    try {
      const response = await axios.get<InternalApiResponse<GraphData[]>>(
        `${baseURL}/api/get-saved-graphs`,
        { params: { id: userId, token: userToken } }
      )

      if (response.data.status === 'success' && response.data.graphs) {
        savedGraphs.value = response.data.graphs.sort(
          (a, b) => new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
        )
      } else {
        toast.error('Error fetching saved graphs.', pve)
      }
    } catch (error) {
      toast.error('Error fetching saved graphs.', pve)
    }
  }

  /**
   * Fetches saved graphs from the server and auto-loads the most recent one (for initial load).
   */
  const fetchSavedGraphs = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return
    }

    try {
      const response = await axios.get<InternalApiResponse<GraphData[]>>(
        `${baseURL}/api/get-saved-graphs`,
        { params: { id: userId, token: userToken } }
      )

      if (response.data.status === 'success' && response.data.graphs) {
        savedGraphs.value = response.data.graphs

        // Sort by modified_at descending and set the most recent as default
        const sortedGraphs = savedGraphs.value.sort(
          (a, b) => new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
        )

        if (sortedGraphs.length > 0) {
          // Check if user has the starter template and prioritize it for new users
          const starterTemplate = sortedGraphs.find(graph => graph.name === 'Starter Strategy')
          if (starterTemplate && sortedGraphs.length === 1) {
            // New user with only the starter template
            selectedGraph.value = starterTemplate.name
            graphName.value = starterTemplate.name
            toast.info('Welcome! We\'ve loaded a starter strategy for you to explore.', pve)
          } else {
            // Existing user with multiple graphs - load most recent
            selectedGraph.value = sortedGraphs[0].name
            graphName.value = sortedGraphs[0].name
          }
          await loadGraphFromServer() // Load the selected graph
        }
      } else {
        toast.error('Error fetching saved graphs.', pve)
      }
    } catch (error) {
      toast.error('Error fetching saved graphs.', pve)
    }
  }

  /**
   * Loads a graph from the server based on the selected graph name.
   */
  const loadGraphFromServer = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return
    }

    if (!selectedGraph.value) {
      toast.error('Please select a graph to load', pve)
      return
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      name: selectedGraph.value,
    }

    try {
      const response = await axios.post<InternalApiResponse<any>>(
        `${baseURL}/api/load-graph`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )
      if (response.data.status === 'success' && response.data.graph_data) {
        if (graph.value) {
          graph.value.clear()
          graph.value.configure(response.data.graph_data)
          graph.value.start()
        }
        if (response.data.start_date) {
          // Handle both date and datetime formats
          const startDateStr = response.data.start_date
          if (startDateStr.includes('T')) {
            // If it already includes time, use as is (but remove milliseconds if present)
            startDate.value = startDateStr.slice(0, 19)
          } else {
            // If it's just a date, add default time (start of day)
            startDate.value = startDateStr + 'T00:00:00'
          }
        }

        if (response.data.end_date) {
          // Handle both date and datetime formats
          const endDateStr = response.data.end_date
          if (endDateStr.includes('T')) {
            // If it already includes time, use as is (but remove milliseconds if present)
            endDate.value = endDateStr.slice(0, 19)
          } else {
            // If it's just a date, add default time (end of day)
            endDate.value = endDateStr + 'T23:59:59'
          }
        }

        if (response.data.symbol) {
          symbol.value = response.data.symbol
        }

        if (response.data.timeframe) {
          timeframe.value = response.data.timeframe
        }
      } else {
        toast.error('Error loading graph', pve)
      }
    } catch (error) {
      toast.error('Error loading graph', pve)
    }
  }

  /**
   * Saves the current graph to the server.
   */
  const saveGraphToServer = async (): Promise<void> => {
    if (!selectedGraph.value) {
      toast.error('Please select a strategy to save.', pve)
      return
    }

    if (!graph.value) {
      toast.error('Graph not initialized.', pve)
      return
    }

    const serializedGraph = graph.value.serialize()
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return
    }
    const sDate = startDate.value
    const eDate = endDate.value
    const tf = timeframe.value
    const sym = symbol.value

    const requestData = {
      user_id: userId,
      token: userToken,
      name: selectedGraph.value,
      graph_data: serializedGraph,
      start_date: sDate,
      end_date: eDate,
      timeframe: tf,
      symbol: sym,
    }

    try {
      const response = await axios.post<InternalApiResponse<null>>(
        `${baseURL}/api/save-graph`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )

      if (response.data.status === 'success') {
        await fetchSavedGraphsList()
      } else {
        toast.error(`Error saving graph.`, pve)
      }
      toast.success('Graph saved successfully.', pve)
    } catch (error) {
      toast.error('Error saving graph.', pve)
    }
  }

  /**
   * Creates a new empty strategy on the server.
   */
  const createEmptyStrategy = async (strategyName: string): Promise<boolean> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return false
    }

    if (!strategyName || !strategyName.trim()) {
      toast.error('Please enter a strategy name', pve)
      return false
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      name: strategyName.trim(),
    }

    try {
      const response = await axios.post<InternalApiResponse<null>>(
        `${baseURL}/api/create-empty-strategy`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )

      if (response.data.status === 'success') {
        toast.success('Empty strategy created successfully.', pve)
        await fetchSavedGraphsList()
        // Set the new strategy as selected
        selectedGraph.value = strategyName.trim()
        graphName.value = strategyName.trim()
        // Load the empty strategy
        await loadGraphFromServer()
        return true
      } else {
        toast.error(response.data.message || 'Error creating strategy', pve)
        return false
      }
    } catch (error: any) {
      if (error.response?.status === 409) {
        toast.error('A strategy with this name already exists', pve)
      } else {
        toast.error('Error creating strategy', pve)
      }
      return false
    }
  }

  /**
   * Deletes a strategy by ID from the server with ownership verification.
   */
  const deleteStrategyById = async (strategyId: number): Promise<boolean> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return false
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      strategy_id: strategyId,
    }

    try {
      const response = await axios.post<InternalApiResponse<null>>(
        `${baseURL}/api/delete-graph`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )

      if (response.data.status === 'success') {
        toast.success('Strategy deleted successfully.', pve)
        
        // Clear selection if the deleted strategy was selected
        const deletedStrategy = savedGraphs.value.find(g => g.id === strategyId)
        if (deletedStrategy && selectedGraph.value === deletedStrategy.name) {
          selectedGraph.value = ''
          graphName.value = ''
          // Clear the graph canvas
          if (graph.value) {
            graph.value.clear()
          }
        }
        
        await fetchSavedGraphsList()
        return true
      } else {
        toast.error(response.data.message || 'Error deleting strategy', pve)
        return false
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error('Strategy not found or you do not have permission to delete it', pve)
      } else {
        toast.error('Error deleting strategy', pve)
      }
      return false
    }
  }

  /**
   * Duplicates a strategy with a new name.
   */
  const duplicateStrategy = async (originalStrategyName: string, newStrategyName: string): Promise<boolean> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User is not authorised', pve)
      return false
    }

    if (!originalStrategyName || !newStrategyName || !newStrategyName.trim()) {
      toast.error('Strategy names are required', pve)
      return false
    }

    // Load the original strategy data
    const requestData = {
      user_id: userId,
      token: userToken,
      name: originalStrategyName,
    }

    try {
      const response = await axios.post<InternalApiResponse<any>>(
        `${baseURL}/api/load-graph`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )

      if (response.data.status === 'success' && response.data.graph_data) {
        // Save as new strategy
        const saveData = {
          user_id: userId,
          token: userToken,
          name: newStrategyName.trim(),
          graph_data: response.data.graph_data,
          start_date: response.data.start_date || startDate.value,
          end_date: response.data.end_date || endDate.value,
          timeframe: response.data.timeframe || timeframe.value,
          symbol: response.data.symbol || symbol.value,
        }

        const saveResponse = await axios.post<InternalApiResponse<null>>(
          `${baseURL}/api/save-graph`,
          saveData,
          { headers: { 'Content-Type': 'application/json' } }
        )

        if (saveResponse.data.status === 'success') {
          toast.success('Strategy duplicated successfully.', pve)
          await fetchSavedGraphsList()
          // Select the new duplicated strategy
          selectedGraph.value = newStrategyName.trim()
          await loadGraphFromServer()
          return true
        } else {
          toast.error(saveResponse.data.message || 'Error duplicating strategy', pve)
          return false
        }
      } else {
        toast.error('Error loading original strategy', pve)
        return false
      }
    } catch (error: any) {
      toast.error('Error duplicating strategy', pve)
      return false
    }
  }

  /**
   * Deletes the selected graph from the server (legacy method - keeping for compatibility).
   */
  const deleteGraphToServer = async (): Promise<void> => {
    if (!selectedGraph.value) {
      toast.error('Please select a graph to delete', pve)
      return
    }

    // Find the selected graph's ID
    const selectedGraphData = savedGraphs.value.find(g => g.name === selectedGraph.value)
    if (!selectedGraphData) {
      toast.error('Selected strategy not found', pve)
      return
    }

    // Use the new ID-based deletion method
    await deleteStrategyById(selectedGraphData.id)
  }

  /**
   * Compiles the selected graph with the specified parameters.
   */
  const compileGraph = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      toast.error('User not authenticated', pve)
      return
    }

    const sDate = startDate.value
    const eDate = endDate.value
    const tf = timeframe.value
    const sym = symbol.value

    if (!selectedGraph.value) {
      toast.error('Please select a graph to compile', pve)
      return
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      name: selectedGraph.value,
      start_date: sDate,
      end_date: eDate,
      timeframe: tf,
      symbol: sym,
    }

    try {
      // Set initial progress state
      compilationProgress.value = {
        isCompiling: true,
        progress: 0,
        stage: 'Starting compilation...',
        graphName: selectedGraph.value
      }

      toast.info('Compilation started...', pve)
      const response = await axios.post<InternalApiResponse<null>>(
        `${baseURL}/api/compile-graph`,
        requestData,
        { headers: { 'Content-Type': 'application/json' } }
      )

      if (response.data.status === 'success') {
        // Progress will be updated via WebSocket events
        // Don't show completion toast here as it will be handled by progress events
      } else {
        toast.error('Error compiling graph.', pve)
        resetCompilationProgress()
      }
    } catch (error: any) {
      resetCompilationProgress()
      // Handle rate limit error (429 status code)
      if (error.response?.status === 429) {
        const retryAfter = error.response?.data?.retry_after || 30
        toast.warning(`Please wait ${retryAfter} seconds before compiling again.`, pve)
      } else {
        toast.error('Error compiling graph.', pve)
      }
    }
  }

  /**
   * Sets default start and end dates.
   */
  const setDefaultDates = (): void => {
    // Set to June 1, 2025 to June 1, 2026
    const startDateObj = new Date('2025-06-01T00:00:00')
    const endDateObj = new Date('2026-06-01T23:59:59')

    // Format as datetime-local string (YYYY-MM-DDTHH:mm:ss)
    startDate.value = startDateObj.toISOString().slice(0, 19)
    endDate.value = endDateObj.toISOString().slice(0, 19)
  }

  const downloadGraph = (): void => {
    if (!graph.value) {
      toast.error('Graph is not initialized.')
      return
    }

    const serializedGraph = graph.value.serialize()
    const graphData = {
      graph: serializedGraph,
      startDate: startDate.value,
      endDate: endDate.value,
      timeframe: timeframe.value,
      symbol: symbol.value,
    }

    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(graphData, null, 2))
    const downloadAnchorNode = document.createElement('a')
    downloadAnchorNode.setAttribute('href', dataStr)
    downloadAnchorNode.setAttribute(
      'download',
      (graphName.value || 'graph') + '.json'
    )
    document.body.appendChild(downloadAnchorNode)
    downloadAnchorNode.click()
    downloadAnchorNode.remove()
  }

  /**
   * Loads a graph from a JSON file and updates the settings.
   */
  function extractFileNameWithoutExtension(fileName: string): string {
    const lastDotIndex = fileName.lastIndexOf('.');
    return lastDotIndex === -1 ? fileName : fileName.substring(0, lastDotIndex);
  }

  const loadGraphFromFile = (graphData: any, fileName?: string): void => {
    // Set the graph name based on the file name if provided,
    // otherwise fall back to the graphData value if available.
    if (fileName) {
      graphName.value = extractFileNameWithoutExtension(fileName);
    } else if (graphData.graphName) {
      graphName.value = graphData.graphName;
    }

    if (graph.value) {
      graph.value.clear();
      graph.value.configure(graphData.graph);
      graph.value.start();
    }

    if (graphData.startDate) {
      // Handle both date and datetime formats
      const startDateStr = graphData.startDate
      if (startDateStr.includes('T')) {
        // If it already includes time, use as is (but remove milliseconds if present)
        startDate.value = startDateStr.slice(0, 19)
      } else {
        // If it's just a date, add default time (start of day)
        startDate.value = startDateStr + 'T00:00:00'
      }
    }
    if (graphData.endDate) {
      // Handle both date and datetime formats
      const endDateStr = graphData.endDate
      if (endDateStr.includes('T')) {
        // If it already includes time, use as is (but remove milliseconds if present)
        endDate.value = endDateStr.slice(0, 19)
      } else {
        // If it's just a date, add default time (end of day)
        endDate.value = endDateStr + 'T23:59:59'
      }
    }
    if (graphData.symbol) {
      symbol.value = graphData.symbol;
    }
    if (graphData.timeframe) {
      timeframe.value = graphData.timeframe;
    }
  }


  const selectedTradeTime = ref<number | null>(null)
  const compilationProgress = ref<{
    isCompiling: boolean;
    progress: number;
    stage: string;
    graphName: string;
  }>({
    isCompiling: false,
    progress: 0,
    stage: '',
    graphName: ''
  })

  function setSelectedTradeTime(timeInUnix: number) {
    selectedTradeTime.value = timeInUnix
  }

  function resetCompilationProgress() {
    compilationProgress.value = {
      isCompiling: false,
      progress: 0,
      stage: '',
      graphName: ''
    }
  }

  // Listen for compilation progress events from WebSocket
  if (typeof window !== 'undefined') {
    window.addEventListener('compilation_progress', (event: Event) => {
      const customEvent = event as CustomEvent;
      const data = customEvent.detail;
      
      if (data.status === 'progress') {
        compilationProgress.value = {
          isCompiling: true,
          progress: data.progress,
          stage: data.stage,
          graphName: data.graph_name
        };
      } else if (data.status === 'completed') {
        compilationProgress.value = {
          isCompiling: false,
          progress: 100,
          stage: data.stage,
          graphName: data.graph_name
        };
        toast.success('Compilation completed successfully!', pve);
        // Reset after a short delay to show completion
        setTimeout(() => {
          resetCompilationProgress();
        }, 3000);
      } else if (data.status === 'error') {
        resetCompilationProgress();
        toast.error(data.message || 'Compilation failed', pve);
      }
    });
  }

  return {
    graph,
    graphCanvas,
    graphName,
    savedGraphs,
    selectedGraph,
    symbolOptions,
    startDate,
    endDate,
    timeframe,
    symbol,
    initializeGraph,
    resizeCanvas,
    populateSymbolDropdown,
    fetchSavedGraphs,
    fetchSavedGraphsList,
    loadGraphFromServer,
    saveGraphToServer,
    deleteGraphToServer,
    createEmptyStrategy,
    deleteStrategyById,
    duplicateStrategy,
    compileGraph,
    setDefaultDates,
    initializeDates,
    downloadGraph,
    loadGraphFromFile,
    selectedTradeTime,
    setSelectedTradeTime,
    compilationProgress,
    resetCompilationProgress,
  }
})
