import networkx as nx
from graphviz import Digraph
from z3 import *


# TODO: process dependency graph to remove cycles by creating supernodes.

class Scheduler:
  stmt_index = {}  # key: statement, value: index of stmt
  stmt_stage = {}  # key: stmt, value: z3 variable for the stage
  stmt_alu = {}  # key: stmt, value: z3 variable for the alu it is assigned to

  def __init__(self, dep_graph, max_stages, max_alus):
    self.dep_graph = dep_graph
    self.max_stages_val = max_stages
    self.max_alus_val = max_alus

    self.create_vars()
    self.opt = Optimize()

  def create_vars(self):
    self.num_stages = Int('stage_num')  # number of stages
    self.num_alus = Int('alu_num')  # number of ALUs per stage

    i = 0
    for u in self.dep_graph.nodes:
      self.stmt_index[u] = i
      i += 1
      self.stmt_stage[u] = Int('stmt_{}_stage'.format(self.stmt_index[u]))
      self.stmt_alu[u] = Int('stmt_{}_alu'.format(self.stmt_index[u]))

  def print_stmt_index(self):
    for u in self.dep_graph.nodes:
      print("{}:{}".format(self.stmt_index[u], u.rstrip()))

  def add_range_constraints(self):
    self.opt.add(self.num_stages <= self.max_stages_val)
    self.opt.add(self.num_alus <= self.max_alus_val)

    for stmt, stage_var in self.stmt_stage.items():
      self.opt.add(stage_var >= 0)
      self.opt.add(stage_var < self.num_stages)

    for stmt, alu_var in self.stmt_alu.items():
      self.opt.add(alu_var >= 0)
      self.opt.add(alu_var < self.num_alus)

  def add_dependency_constraints(self):
    for (u, v) in self.dep_graph.edges:
      self.opt.add(self.stmt_stage[u] < self.stmt_stage[v])

  def add_resource_constraints(self):
    for stmt1 in self.dep_graph.nodes:
      for stmt2 in self.dep_graph.nodes:
        if self.stmt_index[stmt2] > self.stmt_index[stmt1]:
          self.opt.add(Implies(self.stmt_stage[stmt1] == self.stmt_stage[stmt2], \
                               Distinct(self.stmt_alu[stmt1], self.stmt_alu[stmt2])))

  def add_objective(self):
    self.objective = self.num_stages  # minimize number of stages

  def solve(self):
    self.add_range_constraints()
    self.add_resource_constraints()
    self.add_dependency_constraints()
    self.add_objective()

    o = self.opt.minimize(self.objective)
    print(self.opt)

    result = self.opt.check()
    print(result)
    print(self.opt.lower(o))
    m = self.opt.model()
    print(m)

    if result == sat:
      total_alus = 0
      max_alus_per_stage = -1

      num_stages = int(m[self.num_stages].as_string())

      stage_stmt = {}  # key: stage in model, value: list of stmts in that stage

      for stmt, idx in self.stmt_index.items():
        stage = int(m[self.stmt_stage[stmt]].as_string())
        if stage in stage_stmt:
          stage_stmt[stage].append(stmt)
        else:
          stage_stmt[stage] = [stmt]

      # print("stage_stmt", stage_stmt)

      for stage in range(num_stages):
        num_alus = len(stage_stmt[stage])
        print("stage {}: {} ALUs".format(stage, num_alus))
        total_alus += num_alus
        max_alus_per_stage = max(max_alus_per_stage, num_alus)

      print("stmt index")
      self.print_stmt_index()

      print("num_stages", num_stages)
      print("Total number of ALUs", total_alus)
      print("Max ALUS per stage", max_alus_per_stage)
      print("Average number of ALUs per stage", float(total_alus) / num_stages)

  def draw_graph(self):
    dot = Digraph(comment='Dependency graph')
    for node in self.dep_graph.nodes:
      dot.node(node, node)
    for (u, v) in self.dep_graph.edges:
      dot.edge(u, v)

  # dot.node('A', 'King Arthur')
  # dot.node('B', 'Sir Bedevere the Wise')
  # dot.node('L', 'Sir Lancelot the Brave')
  # dot.edges(['AB', 'AL'])
  # dot.edge('B', 'L', constraint='false')

  # dot.render('test-output/dep_graph.gv.png', view=True)
# if __name__ == "__main__":
# 	if len(sys.argv) < 3:
# 		print("Usage: python3 scheduler.py <max number of stages> <max number of ALUs per stage>")
# 		exit(1)

# 	max_stages = int(sys.argv[1])
# 	max_alus = int(sys.argv[2])

# 	sch = Scheduler(define_use, stmt_validity, max_stages, max_alus)
# 	sch.solve()
