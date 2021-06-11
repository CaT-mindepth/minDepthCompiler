

from .. import pass_manager 
from overrides import overrides 
from ..syntax import *
import networkx as nx

class DepGraphSCC(pass_manager.Pass):

    def __init__(self, pm : pass_manager.PassManager):
        super().__init__("DepGraphSCC", ["GenDepGraph", "DepGraphDCE"], pm)
        pm.register(self)
    
    @overrides
    def run(self, deps):
        pass # TODO 

    @overrides 
    def get_output(self):
        pass # TODO 

    def build_SCC_graph(self):  # strongly connected components
        i = 0
        self.scc_graph = nx.DiGraph()
        sccs = []  # list of sccs (list of codelets)

        node_scc = {}  # key: combined node, value: scc
        codelet_node = {}  # key: codelet, value: combined node for scc it belongs to

        for scc in nx.strongly_connected_components(self.dep_graph):
            print("SCC", i)
            sccs.append(scc)

            g = nx.DiGraph()
            g.add_nodes_from(scc)
            scc_edges = []
            for v in scc:
                for e in self.dep_graph.edges([v]):
                    # both nodes in scc, not a rw flank edge
                    if (e[0] in scc) and (e[1] in scc) and (e not in self.read_write_edges):
                        scc_edges.append(e)

            g.add_edges_from(scc_edges)

            # IMP: need to explicitly initialize with [], otherwise old value of combined_node persists
            combined_node = Codelet([])
            for v in nx.topological_sort(g):
                print("v", v, "stmts len", len(v.stmt_list))
                assert(len(v.stmt_list) == 1)  # each codelet has one stmt
                v_text = " ".join([s.get_stmt() for s in v.get_stmt_list()])
                print(v_text)
                combined_node.add_stmts(v.get_stmt_list())
                codelet_node[v] = combined_node

            self.scc_graph.add_node(combined_node)
            combined_node.is_stateful(self.state_variables)
            node_scc[combined_node] = scc

            i += 1

        # add edges

        for node in self.scc_graph.nodes:
            for u in node_scc[node]:
                self.scc_graph.add_edges_from([(node, codelet_node[v]) for v in self.dep_graph.successors(u)
                                               if node != codelet_node[v]])
                self.scc_graph.add_edges_from([(codelet_node[w], node) for w in self.dep_graph.predecessors(u)
                                               if codelet_node[w] != node])

        print("SCC graph nodes")
        print(self.scc_graph.nodes)
        for node in self.scc_graph.nodes:
            node.print()
            if node.is_stateful(self.state_variables):
                self.stateful_nodes.add(node)
                print("stateful")

        print("SCC graph stateful nodes", self.stateful_nodes)
        self.draw_graph(self.scc_graph, self.inputfilename + "_dag")
        print("state vars", self.state_variables)
