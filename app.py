from flask import Flask, render_template, request, jsonify
import folium
import osmnx as ox
import networkx as nx

app = Flask(__name__)

# Load the graph for the Kim Ma Ward, Hanoi (you can adjust this to your region)
G = ox.graph_from_place("Kim Ma, Ba Dinh, Hanoi, Vietnam", network_type='all')


@app.route('/')
def index():
    # Create a Folium map centered on Kim Ma, Hanoi
    m = folium.Map(location=[21.033, 105.825], zoom_start=15)

    # Save map to HTML and render it
    m.save('templates/map.html')
    return render_template('index.html')

@app.route('/find_shortest_path', methods=['POST'])
def find_shortest_path():
    data = request.json
    start_coords = data['start']
    end_coords = data['end']

    # Find the nearest nodes on the graph to the clicked points
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])  # lon, lat
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])

    # Calculate the shortest path using Dijkstra's algorithm
    shortest_path = nx.shortest_path(G, start_node, end_node, weight='length')

    # Get the coordinates for the shortest path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]

    return jsonify(path_coords)

if __name__ == '__main__':
    app.run(debug=True)
