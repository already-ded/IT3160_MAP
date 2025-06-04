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
    data = request.json  # Lấy dữ liệu JSON gửi từ frontend (gồm điểm đầu, điểm cuối, thuật toán, max_depth)
    start_coords = data['start']  # Tọa độ điểm bắt đầu (dạng [lat, lon])
    end_coords = data['end']      # Tọa độ điểm kết thúc (dạng [lat, lon])
    algorithm = data['algorithm'] # Tên thuật toán tìm đường (ví dụ: Dijkstra, BFS, ...)
    max_depth = int(data['max_depth']) # Độ sâu tối đa (nếu thuật toán cần, ví dụ DFS giới hạn độ sâu)

    # Tìm node gần nhất trên bản đồ với tọa độ người dùng chọn
    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])  # lon, lat
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])

    # Lấy hàm thuật toán tương ứng từ danh sách
    func = algorithm_list.get(algorithm)
    if not func:
        return jsonify({"error": "Invalid algorithm selected"}), 400  # Nếu không có thuật toán, trả về lỗi

    # Tính toán đường đi bằng thuật toán đã chọn
    path_coords = []
    if func != DLS and func != IDS:
        path_coords = func(G, start_node, end_node)
    elif func == DLS:
        path_coords = func(G, start_node, end_node, max_depth)
    elif func == IDS:
        path_coords, max_depth = func(G, start_node, end_node)

    if path_coords is None:
        return jsonify({"error": "No path found"}), 404  # Không tìm thấy đường đi

    return jsonify({'path_coords': path_coords, 'max_depth': max_depth})  # Trả về kết quả cho frontend

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
    global G  # Sử dụng biến toàn cục G (đồ thị bản đồ)
    G = ox.load_graphml('trungliet.graphml')  # Tải lại bản đồ từ file gốc
    return jsonify({'message': 'Situation reset successfully'})  # Trả về thông báo thành công

@app.route('/update_road_status', methods=['POST'])
def update_road_status():
    data = request.json  # Lấy dữ liệu JSON từ frontend (gồm tên đường và trạng thái)
    road_name = data.get('road_name')  # Tên đường cần cập nhật
    road_conditions = data.get('road_conditions')  # Danh sách trạng thái (ví dụ: ["Congestion", "Construction"])

    return update_edge_lengths_by_road_status(G, road_conditions, road_name)  # Gọi hàm xử lý chính
def update_edge_lengths_by_road_status(G, road_conditions, road_name):
    status_factor = {
        "Trafic Jam" : 100,
        "Congestion" : 100,
        "Slippery Road" : 100,
        "Construction" : 100,
        "Accidents Ahead": 100
    }

    remove_edges = []
    updated = False

    for u, v, k, data in G.edges(keys=True, data=True):
        edge_name = data.get('name') or data.get('d11')
        if edge_name and str(edge_name) == road_name:
            # Nếu có bất kỳ trạng thái đặc biệt thì xóa cạnh
            if any(cond in status_factor for cond in road_conditions):
                remove_edges.append((u, v, k))
            # else:
            #     # Nếu là trạng thái khác, chỉ tăng length lên (ví dụ: tăng 20%)
            #     for cond in road_conditions:
            #         if cond not in status_factor:
            #             original_length = data['length']
            #             data['length'] = original_length * 1.2
            #             updated = True

    for u, v, k in remove_edges:
        G.remove_edge(u, v, k)
        updated = True

    # Nếu có cập nhật, lưu lại và nạp lại bản đồ để đảm bảo đồng bộ
    if updated:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.graphml') as tmpfile:
            ox.save_graphml(G, tmpfile.name)
            tmpfile.flush()
            G = ox.load_graphml(tmpfile.name)

    return jsonify({
        'road_name': road_name,
        'status': 'removed or updated' if updated else 'no update'
    })

# def update_edge_lengths_by_road_status(G, road_conditions, road_name):
#     status_factor = {
#         "Trafic Jam" : 100,
#         "Congestion" : 100,
#         "Slippery Road" : 100,
#         "Construction" : 100,
#         "Accidents Ahead": 100
#     }

#     updated = False  # Biến kiểm tra có cập nhật gì không
#     for u, v, k, data in G.edges(keys=True, data=True):  # Duyệt qua tất cả các cạnh (đoạn đường)
#         edge_name = data.get('name') or data.get('d11')  # Lấy tên đường của cạnh
#         if edge_name and str(edge_name) == road_name:    # Nếu tên trùng với tên đường cần cập nhật
#             for road_condition in road_conditions:        # Duyệt qua từng trạng thái
#                 if road_condition in status_factor:       # Nếu trạng thái nằm trong bảng hệ số
#                     original_length = data['length']     # Lấy độ dài gốc của cạnh
#                     new_length = original_length * (1 + status_factor[road_condition])  # Tăng độ dài lên nhiều lần
#                     data['length'] = new_length          # Gán lại độ dài mới
#                     updated = True

#     # Nếu có cập nhật, lưu lại và nạp lại bản đồ để đảm bảo đồng bộ
#     if updated:
#         import tempfile
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.graphml') as tmpfile:
#             ox.save_graphml(G, tmpfile.name)
#             tmpfile.flush()
#             G = ox.load_graphml(tmpfile.name)

#     return jsonify({
#         'road_name': road_name,
#         'status': 'updated and graph rebuilt' if updated else 'no update'
#     })
   

# api lấy tên đường
@app.route('/get_roadnames', methods=['GET'])
def get_roadnames():
    road_names_set = set() # để lưu tên đường, tránh trùng lặp
    road_names_list = []   # danh sách kết quả trả về cho frontend

    # Duyệt tất cả các cạnh (edge) trong file graphml
    for edge in root.findall('.//graphml:edge', namespace):
        # Tìm trường dữ liệu d11 (thường là tên đường)
        road_name_d11 = edge.find('./graphml:data[@key="d11"]', namespace)
        # Nếu tìm thấy trường d11 và nó có giá trị (không rỗng)
        if road_name_d11 is not None and road_name_d11.text:
            name = road_name_d11.text
            # Nếu tên đường này chưa có trong tập hợp
            if name not in road_names_set:
                road_names_set.add(name)                # Thêm vào tập hợp (để tránh trùng)
                road_names_list.append({'d11': name})   # Thêm vào danh sách kết quả (dạng dict)
    # Trả về danh sách tên đường cho frontend dưới dạng JSON
    return jsonify(road_names_list)


# lấy thông tin các node
@app.route('/get_node_info', methods=['GET'])
def get_node_info():
    node_names_list = []  # Danh sách kết quả trả về

    # Duyệt qua tất cả các node (nút) trong file graphml
    for node in root.findall('.//graphml:node', namespace):
        # Tìm các trường dữ liệu d8, d11, d5, d4 của node
        node_name_d8 = node.find('./graphml:data[@key="d8"]', namespace)
        node_name_d11 = node.find('./graphml:data[@key="d11"]', namespace)
        node_name_d5 = node.find('./graphml:data[@key="d5"]', namespace)
        node_name_d4 = node.find('./graphml:data[@key="d4"]', namespace)

        node_name_obj = {}  # Tạo một dictionary để lưu thông tin node này

        # Nếu trường d8 có giá trị thì thêm vào dictionary
        if node_name_d8 is not None and node_name_d8.text:
            node_name_obj['d8'] = node_name_d8.text
        # Nếu trường d11 có giá trị thì thêm vào dictionary
        if node_name_d11 is not None and node_name_d11.text:
            node_name_obj['d11'] = node_name_d11.text
        # Nếu trường d5 có giá trị thì thêm vào dictionary
        if node_name_d5 is not None and node_name_d5.text:
            node_name_obj['d5'] = node_name_d5.text
        # Nếu trường d4 có giá trị thì thêm vào dictionary
        if node_name_d4 is not None and node_name_d4.text:
            node_name_obj['d4'] = node_name_d4.text

        # Nếu node này có ít nhất một trường thông tin thì thêm vào danh sách kết quả
        if node_name_obj:
            node_names_list.append(node_name_obj)
    # Trả về danh sách thông tin các node cho frontend dưới dạng JSON
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