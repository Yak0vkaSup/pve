// src/stores/graphStore.ts

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Ref } from 'vue'
import { LGraph, LGraphCanvas, LiteGraph } from 'litegraph.js'
import 'litegraph.js/css/litegraph.css'
import axios from 'axios'

// Import your custom nodes
import '../components/custom_nodes/get/open.js'
import '../components/custom_nodes/get/high.js'
import '../components/custom_nodes/get/low.js'
import '../components/custom_nodes/get/close.js'
import '../components/custom_nodes/get/volume.js'

import '../components/custom_nodes/set/float.js'
import '../components/custom_nodes/set/integer.js'
import '../components/custom_nodes/set/string.js'

import '../components/custom_nodes/tools/add_column.js'
import '../components/custom_nodes/tools/add_condition.js'
import '../components/custom_nodes/tools/get_column.js'

import '../components/custom_nodes/math/multiply_column.js'

import '../components/custom_nodes/logic/_if.js'
import '../components/custom_nodes/logic/_and.js'
import '../components/custom_nodes/logic/_or.js'
import '../components/custom_nodes/logic/_not.js'

import '../components/custom_nodes/compare/cross_over.js'
import '../components/custom_nodes/compare/equal.js'
import '../components/custom_nodes/compare/smaller.js'

import '../components/custom_nodes/indicators/MaNode.js'

// import '../components/custom_nodes/GetDataFromDbNode.js'
// import '../components/custom_nodes/VisualizeDataNode.js'
// import '../components/custom_nodes/indicators/HeikenAshiNode.js'
// import '../components/custom_nodes/MultiplyColumnNode.js'
// import '../components/custom_nodes/indicators/MaNode.js'
// import '../components/custom_nodes/CompareNode.js'


// Define interfaces

// Interface for Bybit API response
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
  const timeframe: Ref<string> = ref('1min')
  const symbol: Ref<string> = ref('')

  /**
   * Initializes the graph and canvas.
   * @param canvasElement - The HTMLCanvasElement to initialize LiteGraphCanvas with.
   */
  const initializeGraph = (canvasElement: HTMLCanvasElement): void => {
    const customLinkTypeColors: Record<string, string>  = {
        integer: "#d2ffb0",
        string: "#f3b0ff",
        boolean: "#F77",
        float: "#b0e0ff",
        column: "#fffdb0"
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
   * @param turnover - The turnover threshold.
   * @returns An array of symbol strings.
   */
  const getSymbolsByTurnover = async (turnover: number): Promise<string[]> => {
    try {
      const response = await axios.get<BybitTickersResponse>(
        'https://api.bybit.com/v5/market/tickers',
        {
          params: { category: 'linear' },
        }
      )

      if (response.data.retCode !== 0) {
        console.error('Failed to get tickers info:', response.data.retMsg)
        return []
      }

      const tickers: Ticker[] = response.data.result.list

      const filteredSymbols = tickers
        .filter((ticker: Ticker) => parseFloat(ticker.turnover24h) > turnover)
        .map((ticker: Ticker) => ticker.symbol)

      console.info(
        `Symbols with turnover greater than ${turnover}:`,
        filteredSymbols
      )
      return filteredSymbols
    } catch (error) {
      console.error('Error fetching symbols:', error)
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
   * Fetches saved graphs from the server.
   */
  const fetchSavedGraphs = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      console.error('User not authenticated')
      return
    }

    try {
      const response = await axios.get<InternalApiResponse<GraphData[]>>(
        'https://pve.finance/api/get-saved-graphs',
        {
          params: { id: userId, token: userToken },
        }
      )

      if (response.data.status === 'success' && response.data.graphs) {
        savedGraphs.value = response.data.graphs

        // Sort by modified_at descending and set the most recent as default
        const sortedGraphs = savedGraphs.value.sort(
          (a, b) => new Date(b.modified_at).getTime() - new Date(a.modified_at).getTime()
        )

        if (sortedGraphs.length > 0) {
          selectedGraph.value = sortedGraphs[0].name
          graphName.value = sortedGraphs[0].name
          await loadGraphFromServer() // Load the default graph
        }
      } else {
        console.error('Error fetching saved graphs:', response.data.message)
      }
    } catch (error) {
      console.error('Error fetching saved graphs:', error)
    }
  }
  /**
   * Loads a graph from the server based on the selected graph name.
   */
  const loadGraphFromServer = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      alert('User not authenticated')
      return
    }

    if (!selectedGraph.value) {
      alert('Please select a graph to load')
      return
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      name: selectedGraph.value,
    }

    try {
      const response = await axios.post<InternalApiResponse<any>>(
        'https://pve.finance/api/load-graph',
        requestData,
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )
      if (response.data.status === 'success' && response.data.graph_data) {
        if (graph.value) {
          graph.value.clear()
          graph.value.configure(response.data.graph_data)
          graph.value.start()
          // resizeCanvas()
        }
        if (response.data.start_date) {
          startDate.value = response.data.start_date.split('T')[0] // Extract date part
        }

        if (response.data.end_date) {
          endDate.value = response.data.end_date.split('T')[0] // Extract date part
        }

        if (response.data.symbol) {
          symbol.value = response.data.symbol
        }

        if (response.data.timeframe) {
          timeframe.value = response.data.timeframe
        }
      } else {
        console.error('Error loading graph:', response.data.message)
      }
    } catch (error) {
      console.error('Error loading graph:', error)
    }
  }

  /**
   * Saves the current graph to the server.
   */
  const saveGraphToServer = async (): Promise<void> => {
    if (!graphName.value) {
      alert('Please enter a graph name.')
      return
    }

    if (!graph.value) {
      alert('Graph not initialized.')
      return
    }

    const serializedGraph = graph.value.serialize()
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      alert('User not authenticated')
      return
    }
    const sDate = startDate.value
    const eDate = endDate.value
    const tf = timeframe.value
    const sym = symbol.value

    const requestData = {
      user_id: userId,
      token: userToken,
      name: graphName.value,
      graph_data: serializedGraph,
      start_date: sDate,
      end_date: eDate,
      timeframe: tf,
      symbol: sym,
    }

    try {
      const response = await axios.post<InternalApiResponse<null>>(
        'https://pve.finance/api/save-graph',
        requestData,
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )

      if (response.data.status === 'success') {
        alert('Graph saved successfully.')
        await fetchSavedGraphs()
      } else {
        alert(`Error: ${response.data.message}`)
      }
    } catch (error) {
      console.error('Error saving graph:', error)
    }
  }

  /**
   * Deletes the selected graph from the server.
   */
  const deleteGraphToServer = async (): Promise<void> => {
    if (!selectedGraph.value) {
      alert('Please select a graph to delete')
      return
    }

    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      alert('User not authenticated')
      return
    }

    const requestData = {
      user_id: userId,
      token: userToken,
      name: selectedGraph.value,
    }

    try {
      const response = await axios.post<InternalApiResponse<null>>(
        'https://pve.finance/api/delete-graph',
        requestData,
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )

      if (response.data.status === 'success') {
        alert('Graph deleted successfully.')
        await fetchSavedGraphs()
      } else {
        alert(`Error: ${response.data.message}`)
      }
    } catch (error) {
      console.error('Error deleting graph:', error)
    }
  }

  /**
   * Compiles the selected graph with the specified parameters.
   */
  const compileGraph = async (): Promise<void> => {
    const userId = localStorage.getItem('userId')
    const userToken = localStorage.getItem('userToken')

    if (!userId || !userToken) {
      alert('User not authenticated')
      return
    }

    const sDate = startDate.value
    const eDate = endDate.value
    const tf = timeframe.value
    const sym = symbol.value

    if (!selectedGraph.value) {
      alert('Please select a graph to compile')
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
      const response = await axios.post<InternalApiResponse<null>>(
        '/api/compile-graph',
        requestData,
        {
          headers: { 'Content-Type': 'application/json' },
        }
      )

      if (response.data.status === 'success') {
        console.log('Compilation started')
      } else {
        console.error('Error compiling graph:', response.data.message)
      }
    } catch (error) {
      console.error('Error:', error)
    }
  }

  /**
   * Sets default start and end dates.
   */
  const setDefaultDates = (): void => {
    const today = new Date()

    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)

    const tomorrow = new Date(today)
    tomorrow.setDate(today.getDate() + 1)

    startDate.value = threeDaysAgo.toISOString().split('T')[0]
    endDate.value = tomorrow.toISOString().split('T')[0]
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
    loadGraphFromServer,
    saveGraphToServer,
    deleteGraphToServer,
    compileGraph,
    setDefaultDates,
  }
})
