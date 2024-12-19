from flask import Flask, render_template, request, jsonify
import osmnx as ox
import networkx as nx
import os
import shutil
from shortest_path_algorithms import *

app = Flask(__name__)

# Unzip the graphml file if neccessary
if os.path.exists('./data/graph.graphml') == False: 
    shutil.unpack_archive('data.zip', '.')

G = ox.load_graphml('./data/graph.graphml')

# Ensure future commits don't have large file
os.remove('./data/graph.graphml') 
os.removedirs('./data')
@app.route('/')
def index():
    node_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in G.nodes]
    return render_template('index.html', node_coords=node_coords)

algorithm_list = {
    'Dijkstra': Dijkstra, 
    'DFS': DFS, 
    'BFS': BFS, 
    'A Star': A_Star, 
    'Depth Limited DFS': DLS,
    'Greedy Search': GFS
}
@app.route('/find_shortest_path', methods=['POST'])
def find_shortest_path():
    data = request.json
    start_coords = data['start']
    end_coords = data['end']
    algorithm = data['algorithm']
    max_depth = int(data['max_depth'])
    # Find the nearest nodes on the graph to the clicked points
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])  # lon, lat
    print(start_coords)
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    print(end_coords)
    
    func = algorithm_list.get(algorithm)
    if not func:
        return jsonify({"error": "Invalid algorithm selected"}), 400

    # Calculate the path using the selected algorithm
    path_coords = []
    if func != DLS:
        path_coords = func(G, start_node, end_node)
    else:
        path_coords = func(G, start_node, end_node, max_depth)

    if path_coords is None:
        return jsonify({"error": "No path found"}), 404

    return jsonify(path_coords)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
