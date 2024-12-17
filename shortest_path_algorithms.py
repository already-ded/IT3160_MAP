import networkx as nx
def DFS(G, start_node, end_node):
    dfs_edges = list(nx.dfs_edges(G, source=start_node))
    path = []
    parent = {v:u for u, v in dfs_edges}
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

def depth_limited_DFS(G, start_node, end_node, max_depth):
    def recursive_dls(node, depth):
        if node == end_node:
            return [node]
        if depth == 0:
            return None
        for neighbor in G.neighbors(node):
            path = recursive_dls(neighbor, depth - 1)
            if path:
                return [node] + path
        return None

    path = recursive_dls(start_node, max_depth)
    if path is None:
        return None

    # Get the coordinates for the path
    path_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in path]
    return path_coords
