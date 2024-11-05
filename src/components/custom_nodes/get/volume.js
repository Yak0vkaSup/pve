// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetVolumeNode() {
  this.addOutput('volume', 'column')

  this.serialize_widgets = true
}

GetVolumeNode.title = 'Get volume'

LiteGraph.registerNodeType('get/volume', GetVolumeNode)
