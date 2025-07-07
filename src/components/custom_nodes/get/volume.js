// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function GetVolumeNode() {
  this.addOutput('volume', 'float')

  this.serialize_widgets = true
}

GetVolumeNode.title = 'Get volume'

LiteGraph.registerNodeType('get/volume', GetVolumeNode)
