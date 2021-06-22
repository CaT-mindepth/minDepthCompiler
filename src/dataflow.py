#
# dataflow.py - forward dataflow analysis 
#
# let w = new set with all nodes
# repeat until w is empty
#  let n = w.pop()
#  old_out = out[n]
#  let in = combine(preds[n])
#  out[n] := flow[n](in)
#  if (!equal old_out out[n]),
#    for all m in succs[n], w.add(m)
# end

from dependencyGraph import DependencyGraph

class Lattice(object):
    def __init__(self):
        self.out = []
    
    

def fix(g : DependencyGraph):
    w = []
    for node in g.comp_graph:
        w.append(node)
    
    while len(w) != 0:
        n = w.pop()
        old_out = 
