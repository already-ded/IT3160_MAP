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
    node_coords = []
    for node in G.nodes:
        y = G.nodes[node]['y']
        x = G.nodes[node]['x']
        name = G.nodes[node].get('name', str(node))
        node_coords.append({'coord': [y, x], 'name': name})

    path_coords = []
    for u, v, data in G.edges(data=True):
        coords = [[G.nodes[u]['y'], G.nodes[u]['x']], [G.nodes[v]['y'], G.nodes[v]['x']]]
        # Use d11 as name if available, else use edge id
        name = data.get('name') or data.get('d11') or f"{u} - {v}"
        path_coords.append({'coords': coords, 'name': name})

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
    road_name_d8 = edge.find('./graphml:data[@key="d8"]', namespace)
    road_name_d11 = edge.find('./graphml:data[@key="d11"]', namespace)
    
    road_name = None
    if road_name_d11 is not None and road_name_d11.text:
        road_name = road_name_d11.text
    elif road_name_d8 is not None and road_name_d8.text:
        road_name = road_name_d8.text
        
    if road_name:
        road_names.add(road_name)

# Chuyển danh sách roadname thành dạng sắp xếp
road_names = sorted(road_names)

# Dictionary to store road status information
road_status_dict = {}


@app.route('/reset_situation', methods=['POST'])
def reset_situation():
    global G
    G = ox.load_graphml('trungliet.graphml')
    return jsonify({'message': 'Situation reset successfully'})

@app.route('/update_road_status', methods=['POST'])
def update_road_status():
    data = request.json
    road_name = data.get('road_name')
    road_conditions = data.get('road_conditions')

    return update_edge_lengths_by_road_status(G, road_conditions, road_name)

def update_edge_lengths_by_road_status(G, road_conditions, road_name):
    status_factor = {
        "Trafic Jam" : 100,
        "Congestion" : 100,
        "Slippery Road" : 100,
        "Construction" : 100,
        "Accidents Ahead": 100
    }

    updated = False
    for u, v, k, data in G.edges(keys=True, data=True):
        edge_name = data.get('name') or data.get('d11')
        if edge_name and str(edge_name) == road_name:
            for road_condition in road_conditions:
                if road_condition in status_factor:
                    original_length = data['length']
                    new_length = original_length * (1 + status_factor[road_condition])
                    data['length'] = new_length
                    updated = True

    # Rebuild the graph (optional, only if you need to refresh structure)
    if updated:
        # Convert to GraphML string and reload (to refresh structure)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.graphml') as tmpfile:
            ox.save_graphml(G, tmpfile.name)
            tmpfile.flush()
            G = ox.load_graphml(tmpfile.name)

    return jsonify({
        'road_name': road_name,
        'status': 'updated and graph rebuilt' if updated else 'no update'
    })

@app.route('/get_roadnames', methods=['GET'])
def get_roadnames():
    road_names_set = set()
    road_names_list = []
    for edge in root.findall('.//graphml:edge', namespace):
        road_name_d11 = edge.find('./graphml:data[@key="d11"]', namespace)
        if road_name_d11 is not None and road_name_d11.text:
            name = road_name_d11.text
            if name not in road_names_set:
                road_names_set.add(name)
                road_names_list.append({'d11': name})
    return jsonify(road_names_list)

@app.route('/get_node_info', methods=['GET'])
def get_node_info():
    node_names_list = []
    for node in root.findall('.//graphml:node', namespace):
        node_name_d8 = node.find('./graphml:data[@key="d8"]', namespace)
        node_name_d11 = node.find('./graphml:data[@key="d11"]', namespace)
        node_name_d5 = node.find('./graphml:data[@key="d5"]', namespace)
        node_name_d4 = node.find('./graphml:data[@key="d4"]', namespace)

        node_name_obj = {}
        if node_name_d8 is not None and node_name_d8.text:
            node_name_obj['d8'] = node_name_d8.text
        if node_name_d11 is not None and node_name_d11.text:
            node_name_obj['d11'] = node_name_d11.text
        if node_name_d5 is not None and node_name_d5.text:
            node_name_obj['d5'] = node_name_d5.text
        if node_name_d4 is not None and node_name_d4.text:
            node_name_obj['d4'] = node_name_d4.text
        if node_name_obj:
            node_names_list.append(node_name_obj)
    return jsonify(node_names_list)

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