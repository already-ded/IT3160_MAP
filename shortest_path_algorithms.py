import networkx as nx
from queue import PriorityQueue
def DFS(G, start_node, end_node):
    visited = set()
    parent = {}
    s = []
    s.append(start_node)
    while (len(s) > 0):
        node = s.pop()
        if node in visited:
            continue
        visited.add(node)
        for neighbors in G.neighbors(node):
            if neighbors in visited:
                continue
            parent[neighbors] = node
            s.append(neighbors)

    if end_node not in parent:
        return None

    path = []
    node = end_node
    while node != start_node:
        path.append(node)
        node = parent[node]
    path.append(start_node)
    # Get the coordinates for the path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
    return path_coords


def BFS(G, start_node, end_node):
    bfs_edges = list(nx.bfs_edges(G, source=start_node))
    path = []
    parent = {v:u for u, v in bfs_edges}

    if end_node not in parent:
        return None
    
    node = end_node
    while node != start_node:
        path.append(node)
        node = parent[node]
    path.append(start_node)

    # Get the coordinates for the path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
    return path_coords

def Dijkstra(G, start_node, end_node):
    shortest_path = nx.shortest_path(G, start_node, end_node, weight='length')

    # Get the coordinates for the shortest path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]
    return path_coords

def A_Star(G, start_node, end_node):
    shortest_path = nx.astar_path(G, start_node, end_node, weight='length')
    # Get the coordinates for the shortest path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in shortest_path]
    return path_coords

def DLS(G, start_node, end_node, max_depth):
    visited = set()
    parent = {}
    s = [] 
    s.append((start_node, 0))  # Each stack element is (node, current_depth)
    
    while len(s) > 0:
        node, depth = s.pop()
        if depth > max_depth:
            continue
        if node in visited:
            continue
        visited.add(node)
        for neighbor in G.neighbors(node):
            if neighbor in visited:
                continue
            parent[neighbor] = node
            s.append((neighbor, depth + 1))
            
    if end_node not in parent:
        return None
    
    path = []
    node = end_node
    while node != start_node:
        path.append(node)
        node = parent[node]
    path.append(start_node)
    
    # Get the coordinates for the path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
    return path_coords

def IDS(G, start_node, end_node):
    max_depth = 0
    while (DLS(G, start_node, end_node, max_depth) is None):
        max_depth += 1
    print(max_depth)
    return (DLS(G, start_node, end_node, max_depth), max_depth)

def GFS(G, start_node, end_node):
    def heuristic(G, node, goal):
        x1, y1 = G.nodes[node]['x'], G.nodes[node]['y']
        x2, y2 = G.nodes[goal]['x'], G.nodes[goal]['y']
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
    
    visited = set()
    q = PriorityQueue()
    q.put((0, start_node))
    parent = {}

    while not q.empty():
        _, current_node = q.get()
        if current_node in visited:
            continue
        visited.add(current_node)

        if current_node == end_node:
            break

        for neighbor in G.neighbors(current_node):
            print(neighbor)
            if neighbor not in visited:
                priority = heuristic(G, neighbor, end_node)
                q.put((priority, neighbor))
                parent[neighbor] = current_node

    if end_node not in parent:
        return None

    path = []
    node = end_node
    while node != start_node:
        path.append(node)
        node = parent[node]
    path.append(start_node)
    #path.reverse()
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
    return path_coords