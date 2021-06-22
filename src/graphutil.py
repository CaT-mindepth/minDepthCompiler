
import networkx as nx

def dfs(G : nx.DiGraph, D, v, p):
    D[v] = max(D[v], D[p] + 1) # relax 
    for x in G.successors(v):
        dfs(G, D, x, v)

# computes the length of longest path from source in G. Assuming that G is a dag.
def longest_path_from_src(G : nx.DiGraph, u):
    D = {}
    src_nodes = []
    virtual_src = '__virt__'
    D[virtual_src] = -1
    for v in G.nodes: 
        D[v] = 0
        if len(list(G.predecessors(v))) == 0:
            src_nodes.append(v)
    for v in src_nodes: 
        # print(' -> src node: ', v)
        dfs(G, D, v, virtual_src)
    return D[u]

# computes the length of longest path to sink in G. Assuming that G is a dag.
def longest_path_to_sink(G : nx.DiGraph, u):
    D = {} 
    sink_nodes = []
    D[u] = 0 
    for v in G.nodes: 
        D[v] = 0 
        if len(list(G.successors(v))) == 0:
            sink_nodes.append(v)
    for v in G.successors(u):
        dfs(G, D, v, u)
    max_length = 0 
    for x in sink_nodes: 
        max_length = max(max_length, D[x])
    return max_length

# computes length of longest path in G
def len_longest_path_in(G: nx.DiGraph):
    return nx.dag_longest_path_length(G)

# decides if merging two adjacent nodes in a dag G increases the depth 
# (i.e. longest path length) of G.
def merge_increases_depth(G : nx.DiGraph, u, v):
    assert (u in G.nodes) and (v in G.nodes) 
    x = (longest_path_from_src(G, u)) + (longest_path_to_sink(G, v))
    y = (longest_path_from_src(G, v)) + (longest_path_to_sink(G, u))
    orig_d = len_longest_path_in(G)
    return (x > orig_d or y > orig_d) 