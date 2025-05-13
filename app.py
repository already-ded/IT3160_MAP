from flask import Flask, render_template, request, jsonify
import osmnx as ox
import networkx as nx
import os
import shutil
import xml.etree.ElementTree as et
from shortest_path_algorithms import *

app = Flask(__name__)


G = ox.load_graphml('trungliet.graphml')

@app.route('/')
def index():
    node_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in G.nodes]
    path_coords = [
        [(G.nodes[e[0]]['y'], G.nodes[e[0]]['x']), (G.nodes[e[1]]['y'], G.nodes[e[1]]['x'])]
        for e in G.edges
    ]
    return render_template('index.html', node_coords=node_coords, path_coords=path_coords)

algorithm_list = {
    'Dijkstra': Dijkstra, 
    'DFS': DFS, 
    'BFS': BFS, 
    'A Star': A_Star, 
    'Depth Limited DFS': DLS,
    'Iterative Deepening Search': IDS,
    'Greedy Search': GFS
}
@app.route('/find_shortest_path', methods=['POST'])
def find_shortest_path():
    data = request.json
    start_coords = data['start']
    end_coords = data['end']
    algorithm = data['algorithm']
    max_depth = int(data['max_depth']) # if not specified, max_depth is 0
    # Find the nearest nodes on the graph to the clicked points
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])  # lon, lat
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    
    func = algorithm_list.get(algorithm)
    if not func:
        return jsonify({"error": "Invalid algorithm selected"}), 400

    # Calculate the path using the selected algorithm
    path_coords = []
    if func != DLS and func != IDS:
        path_coords = func(G, start_node, end_node)
    elif func == DLS:
        path_coords = func(G, start_node, end_node, max_depth)
    elif func == IDS:
        path_coords, max_depth = func(G, start_node, end_node)

    if path_coords is None:
        return jsonify({"error": "No path found"}), 404

    return jsonify({'path_coords': path_coords, 'max_depth': max_depth})

# Đường dẫn tương đối đến file graphml
graphml_file = os.path.join(os.path.dirname(__file__), 'trungliet.graphml')

# Parse file graphml để lấy danh sách roadname
tree = et.parse(graphml_file)
root = tree.getroot()

# Namespace của GraphML
namespace = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}

# Trích xuất các roadname
road_names = set()
for edge in root.findall('.//graphml:edge', namespace):
    road_name = edge.find('./graphml:data[@key="d11"]', namespace)
    if road_name is not None and road_name.text:
        road_names.add(road_name.text)

# Chuyển danh sách roadname thành dạng sắp xếp
road_names = sorted(road_names)

@app.route('/get_roadnames', methods=['GET'])
def get_roadnames():
    # API để gửi danh sách roadname đến frontend
    return jsonify(road_names)

@app.route('/get_road_geometry', methods=['POST'])
def get_road_geometry():
    road_name = request.json.get('road_name')
    if not road_name:
        return jsonify({'error': 'Missing road_name'}), 400

    namespace = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}
    tree = et.parse(graphml_file)
    root = tree.getroot()

    # Tạo lại key_map như trước (có thể dùng chung nếu đã khai báo toàn cục)
    key_map = {}
    for key in root.findall('graphml:key', namespace):
        key_map[key.attrib.get('id')] = key.attrib.get('attr.name')

    # Tìm các cạnh (edges) có tên khớp với road_name
    matched_edges = []
    for edge in root.findall('.//graphml:edge', namespace):
        edge_name = None
        for data in edge.findall('graphml:data', namespace):
            if key_map.get(data.attrib.get('key')) == 'name':
                edge_name = data.text
                break
        if edge_name != road_name:
            continue

        # Lấy id của 2 node đầu-cuối
        source = edge.attrib.get('source')
        target = edge.attrib.get('target')

        # Lấy tọa độ từ graph G
        try:
            coord1 = (G.nodes[source]['y'], G.nodes[source]['x'])
            coord2 = (G.nodes[target]['y'], G.nodes[target]['x'])
            matched_edges.append([coord1, coord2])
        except:
            continue

    return jsonify({'segments': matched_edges})

if __name__ == '__main__':
    app.run(debug=True, port=8000)