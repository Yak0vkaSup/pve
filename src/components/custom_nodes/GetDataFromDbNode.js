// Import LiteGraph
import { LiteGraph } from 'litegraph.js'
import axios from 'axios'
LiteGraph.clearRegisteredTypes();

export function GetDataFromDbNode() {
  this.addOutput('open', 'column')
  this.addOutput('high', 'column')
  this.addOutput('low', 'column')
  this.addOutput('close', 'column')
  this.addOutput('volume', 'column')

  const getFormattedDate = (date) => {
    return date.toISOString().split('T')[0].replace(/-/g, '/')
  }

  const getDateDaysAgo = (days) => {
    const date = new Date()
    date.setDate(date.getDate() - days)
    return date
  }

  const today = new Date()
  const fiveDaysAgo = getDateDaysAgo(5)

  this.properties = {
    symbol: 'BTCUSDT',
    startDate: getFormattedDate(fiveDaysAgo),
    endDate: getFormattedDate(today)
  }

  const getSymbolsByTurnover = async (turnover) => {
    try {
      const response = await axios.get('https://api.bybit.com/v5/market/tickers', {
        params: { category: 'linear' }
      })

      if (response.data.retCode !== 0) {
        console.error('Failed to get tickers info')
        return []
      }

      const filteredSymbols = response.data.result.list
        .filter((ticker) => parseFloat(ticker.turnover24h) > turnover)
        .map((ticker) => ticker.symbol)

      console.info(`Symbols with turnover greater than ${turnover}:`, filteredSymbols)
      return filteredSymbols
    } catch (error) {
      console.error('Error fetching symbols:', error)
      return []
    }
  }

  getSymbolsByTurnover(50000000).then((symbols) => {
    this.addWidget(
      'combo',
      'symbol',
      this.properties.symbol,
      (value) => {
        this.properties.symbol = value
      },
      {
        values: symbols.length > 0 ? symbols : ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
      }
    )
  })

  this.serialize_widgets = true
}

GetDataFromDbNode.title = 'Get data'

LiteGraph.registerNodeType('custom/getdata', GetDataFromDbNode)
