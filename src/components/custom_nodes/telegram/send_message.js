// Import LiteGraph
import { LiteGraph } from 'litegraph.js'

export function SendMessageNode() {
  this.addInput('Exec', 'exec')
  this.addInput('Message', 'string')
  this.addInput('UserID', 'int')

  this.addOutput('Exec', 'exec')

  this.serialize_widgets = true;
}

SendMessageNode.title = 'Send Message'

LiteGraph.registerNodeType('telegram/send_message', SendMessageNode)
