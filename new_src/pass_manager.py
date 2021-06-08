
import networkx as nx 

class Pass(object):
    def __init__(self, name, dependencies : list[str], pass_manager):
        self.name = name 
        self.dependencies = dependencies 
        self.pass_manager = pass_manager 
        pass_manager.register(self)
        self.has_ran = False # set to True after the run(...) method is called.

    def __str__(self):
        return self.name 

    def run(self, dependend_passes):
        pass 

    def get_output(self):
        pass 

class PassManager(object):
    def __init__(self, name : str):
        self.name = name 
        self.pass_graph = nx.Digraph() 
        self.passes = []
        self.pass_name_to_pass = {} 

    def register(self, pass_ : Pass):
        self.passes.append(pass_)
        self.pass_name_to_pass[str(pass_)] = pass_ 
        if not (pass_ in self.pass_graph):
            self.pass_graph.add_node(pass_)
        for pass_dep in pass_.dependencies:
            self.pass_graph.add_edge(self.pass_graph[self.pass_name_to_pass[pass_dep]], pass_)
        
    def schedule(self):
        for p in nx.topological_sort(self.pass_graph):
            prev_dependencies = list(map(lambda x : self.pass_name_to_pass(x), p.dependencies))
            p.run(prev_dependencies)
    
    def list_passes(self):
        for p in nx.topological_sort(self.pass_graph):
            print("Pass " + str(p))
            print(" (dependencies: " + str(p.dependencies) + ')')