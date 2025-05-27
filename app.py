from flask import Flask, render_template, request, jsonify
import osmnx as ox
import networkx as nx
import xml.etree.ElementTree as ET
from shortest_path_algorithms import *

app = Flask(__name__)

# Load the graph from trungliet.graphml
G = ox.load_graphml('trungliet.graphml')


# Đường dẫn tới file trungliet.graphml
graphml_file = r'c:\Users\admin\Downloads\IT3160_MAP-main\IT3160_MAP-main\trungliet.graphml'

# Parse file graphml để lấy danh sách roadname
tree = ET.parse(graphml_file)
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

road_status_dict = {}

@app.route('/update_road_status', methods=['POST'])
def update_road_status():
    data = request.json
    road_name = data.get('road_name')
    road_conditions = data.get('road_conditions')
    if not road_name or not road_conditions:
        return jsonify({'message': 'Missing information'}), 400
    road_status_dict[road_name] = road_conditions
    update_edge_lengths_by_road_status(G, road_status_dict)

    # lấy danh sách length mới của các canh thuộc road_name vừa cập nhật
    new_lengths = []
    for u, v, k, edge_data in G.edges(keys=True, data=True):
        if edge_data.get('road_name') == road_name:
            new_lengths.append({
                'from': u,
                'to': v,
                'key': k,
                'length': edge_data.get('length', 0)
            })
    return jsonify({
        'message': f'Updated status for {road_name}!',
        'new_lengths': new_lengths
    })    

def update_edge_lengths_by_road_status(G, road_status_dict):
    # Cập nhật lại length của các cạnh trong đồ thị G dựa vào road_status_dict.

    # Hệ số tăng length cho từng tình huống
    status_factor = {
        'traffic jam': 0.4,
        'congestion': 0.3,
        'slippery road': 0.15,
        'construction': 0.2,
        'accidents ahead': 0.25
    }

    for u, v, k, data in G.edges(keys=True, data=True):
        road_name = data.get('road_name')
        if not road_name:
            continue
        # Nếu tên đường có trong dict trạng thái
        if road_name in road_status_dict:
            factors = road_status_dict[road_name]
            # Nhân các hệ số nếu tình huống
            total_multiplier = 1.0
            for f in factors:
                total_multiplier *= (1 + status_factor.get(f, 0))
            original_length = data.get('length', 0)
            data['length'] = original_length * total_multiplier


@app.route('/')
def index():
    # Lấy tọa độ các node và edges để hiển thị trên bản đồ
    node_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in G.nodes]
    path_coords = [
        [(G.nodes[e[0]]['y'], G.nodes[e[0]]['x']), (G.nodes[e[1]]['y'], G.nodes[e[1]]['x'])]
        for e in G.edges
    ]
    return render_template('index.html', node_coords=node_coords, path_coords=path_coords)



# Danh sách thuật toán tìm đường
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
    max_depth = int(data.get('max_depth', 0))  # Nếu không được chỉ định, max_depth mặc định là 0

    # Tìm node gần nhất trên đồ thị với tọa độ được chọn
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])  # lon, lat
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])
    
    func = algorithm_list.get(algorithm)
    if not func:
        return jsonify({"error": "Invalid algorithm selected"}), 400

    # Tính toán đường đi bằng thuật toán được chọn
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

if __name__ == '__main__':
    app.run(debug=True, port=8000)