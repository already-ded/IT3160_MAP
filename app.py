from flask import Flask, render_template, request, jsonify
import folium
import osmnx as ox
import networkx as nx
from shortest_path_algorithms import *
app = Flask(__name__)

# Load the graph for the Kim Ma Ward, Hanoi (you can adjust this to your region)
G = ox.load_graphml('data/graph.graphml') #("Ba Dinh District, Hanoi, Vietnam", network_type='all')

@app.route('/')
def index():
    # Create a Folium map centered on Kim Ma, Hanoi
    m = folium.Map(location=[21.033, 105.825], zoom_start=15)

    # Save map to HTML and render it
    return render_template('index.html')

algorithm_list = {
    'Dijkstra': Dijkstra, 
    'DFS': DFS, 
    'BFS': BFS, 
    'A Star': A_Star, 
    'Depth Limited DFS': depth_limited_DFS
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
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    
    func = algorithm_list.get(algorithm)
    if not func:
        return jsonify({"error": "Invalid algorithm selected 1 2 3"}), 400

    # Calculate the path using the selected algorithm
    path_coords = []
    if func != depth_limited_DFS:
        path_coords = func(G, start_node, end_node)
    else:
        path_coords = func(G, start_node, end_node, max_depth)

    if path_coords is None:
        return jsonify({"error": "No path found"}), 404

    return jsonify(path_coords)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
