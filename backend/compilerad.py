import pandas as pd
import json

class Node:
    def __init__(self, node_data):
        self.id = node_data['id']
        self.type = node_data['type']
        self.properties = node_data['properties']
        self.inputs = node_data.get('inputs', [])
        self.outputs = node_data.get('outputs', [])
    
    def __repr__(self):
        return f"Node(id={self.id}, type={self.type}, properties={self.properties})"

def find_node_by_output_link(link_id, nodes):
    """Trouver un noeud et un output correspondant à un lien."""
    for node in nodes:
        for output in node.get('outputs', []):
            # On s'assure que 'links' est une liste avant de l'itérer
            links = output.get('links', [])
            if links is not None and link_id in links:
                return node, output['name']
    return None, None

def compile(graph_data):
    nodes = graph_data['nodes']
    
    # Carte des nœuds pour un accès rapide par ID
    nodes_map = {node['id']: node for node in nodes}

    # Parcourir les nœuds pour vérifier leurs inputs
    for node in nodes:
        for input_ in node.get('inputs', []):
            link_id = input_.get('link')
            if link_id is not None:
                # Trouver le nœud source et l'output correspondant
                source_node, source_output_name = find_node_by_output_link(link_id, nodes)
                
                if source_node and source_output_name:
                    # Afficher la connexion
                    print(f"Node {node['type']} receives '{input_['name']}' input from "
                          f"Node {source_node['type']} (output '{source_output_name}') via link {input_['type']}")

if __name__ == "__main__":
    jsonpve = """
    {"extra": {},
"links": [[1,2,0,1,0,"dataframe"],[2,3,0,1,4,"list"],[3,2,3,4,0,"dataframe"],[4,2,3,5,0,"dataframe"],[5,5,0,3,1,"dataframe"],[6,5,1,3,2,"dataframe"],[7,5,2,3,3,"dataframe"],[8,4,0,3,0,"dataframe"],[9,2,3,7,0,"dataframe"],[10,7,0,3,4,"dataframe"]],
"nodes": [{"id": 5,"pos": [354,370],"mode": 0,"size": {"0": 140,"1": 66},
"type": "custom/indicators/bollinger","flags": {},"order": 3,
    "inputs": [
        {"link": 4,"name": "Close","type": "dataframe"}],
    "outputs": [
        {"name": "Lower","type": "dataframe","links": [5],"slot_index": 0},
        {"name": "Mid","type": "dataframe","links": [6],"slot_index": 1},
        {"name": "Upper","type": "dataframe","links": [7],"slot_index": 2}],"properties": {"windows": 7}},{"id": 7,"pos": [217,506],"mode": 0,"size": {"0": 210,"1": 58},
"type": "custom/indicators/ma","flags": {},"order": 4,
    "inputs": [
        {"link": 9,"name": "Close","type": "dataframe"}],
    "outputs": [
        {"name": "ma","type": "dataframe","links": [10],"slot_index": 0}],"properties": {"Mode": "ema","Window": 7}},{"id": 3,"pos": [620,348],"mode": 0,"size": {"0": 253.60000610351562,"1": 162},
"type": "custom/data/getallindicatorsnode","flags": {},"order": 5,
    "inputs": [
        {"link": 8,"name": "Indicator","type": "dataframe"},
        {"link": 5,"name": "Indicator 2","type": "dataframe"},
        {"link": 6,"name": "Indicator 3","type": "dataframe"},
        {"link": 7,"name": "Indicator 4","type": "dataframe"},
        {"link": 10,"name": "Indicator 5","type": "dataframe"}],
    "outputs": [
        {"name": "List of indicators","type": "list","links": [2],"slot_index": 0}],"properties": {"factor": 1,"numInputs": 5}},{"id": 1,"pos": [1101,187],"mode": 0,"size": {"0": 140,"1": 106},
"type": "custom/vizualize","flags": {},"order": 6,
    "inputs": [
        {"link": 1,"name": "Open","type": "dataframe"},
        {"link": null,"name": "High","type": "dataframe"},
        {"link": null,"name": "Low","type": "dataframe"},
        {"link": null,"name": "Close","type": "dataframe"},
        {"link": 2,"name": "Indicators list","type": "list"}],"properties": {}},{"id": 4,"pos": [411,243],"mode": 0,"size": {"0": 140,"1": 26},
"type": "custom/indicators/rsi","flags": {},"order": 2,
    "inputs": [
        {"link": 3,"name": "Close","type": "dataframe"}],
    "outputs": [
        {"name": "rsi","type": "dataframe","links": [8],"slot_index": 0}],"properties": {"windows": 7}},{"id": 2,"pos": [166,117],"mode": 0,"size": {"0": 140,"1": 106},
"type": "custom/data/get","flags": {},"order": 0,
    "outputs": [
        {"name": "Open","type": "dataframe","links": [1],"slot_index": 0},
        {"name": "High","type": "dataframe","links": null},
        {"name": "Low","type": "dataframe","links": null},
        {"name": "Close","type": "dataframe","links": [3,4,9],"slot_index": 3},
        {"name": "Volume","type": "dataframe","links": null}],"properties": {"symbol": "TONUSDT","endDate": "2024/09/29","precision": 1,"startDate": "2024/09/26"}},{"id": 9,"pos": [728,-6],"mode": 0,"size": {"0": 140,"1": 26},
"type": "custom/data/multiplycolumnnode","flags": {},"order": 1,
    "inputs": [
        {"link": null,"name": "Df","type": "dataframe"}],
    "outputs": [
        {"name": "Df","type": "dataframe","links": null}],"properties": {"factor": 1}}],"config": {},"groups": [],"version": 0.4,"last_link_id": 10,"last_node_id": 9}
    """
    graph_data=json.loads(jsonpve)
    compile(graph_data)