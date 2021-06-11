
from .. import pass_manager 
from overrides import overrides 
from graphviz import Digraph

class DepGraphDraw(pass_manager.Pass):
    def __init__(self, pm : pass_manager.PassManager, graph_file : str):
        super().__init__("DepGraphDraw", ["GenDepGraph", "DepGraphSCC"], pm)
        self.graph_file = graph_file
        pm.register(self)
    
    @overrides 
    def run(self, deps):
        self.draw_graph(deps[0].get_output(), self.graph_file + "_orig.dot", "Dependency graph")
        self.draw_graph(deps[1].get_output(), self.graph_file + "_SCC.dot", "Dependency graph SCC")

    @overrides 
    def get_output(self):
        pass 

    def draw_graph(self, graph, graphfile, graph_name):
        dot = Digraph(comment=graph_name)
        node_stmts = {}
        for node in graph.nodes:
            stmt_list = node.get_stmt_list()
            stmt_text = " ".join([s.get_stmt().replace(":", "|")
                                 for s in stmt_list])
            dot.node(stmt_text)
            node_stmts[node] = stmt_text

        for (u, v) in graph.edges:
            dot.edge(node_stmts[u], node_stmts[v])

        dot.render(graphfile, view=True)
