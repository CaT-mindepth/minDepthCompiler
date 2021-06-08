
import networkx as nx 

class Pass(object):
    def __init__(self, name, dependencies : list[str], pass_manager):
        self.name = name 
        self.dependencies = dependencies 
        self.pass_manager = pass_manager 
        pass_manager.register(self)

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

    def register(self, pass : Pass):
        self.passes.append(pass)
        self.pass_name_to_pass 
    
    def schedule(self):
        for p in nx.topological_sort(self.pass_graph):
            prev_dependencies = list(map(lambda x : self.pass_name_to_pass(x), p.dependencies))
            p.run(prev_dependencies)
    
    def list_passes(self):
        for p in nx.topological_sort(self.pass_graph):
            print("Pass " + str(p))
            print(" (dependencies: " + str(p.dependencies) + ')')