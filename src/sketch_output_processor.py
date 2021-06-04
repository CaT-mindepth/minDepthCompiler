import sys
import lexerRules
import ply.lex as lex
import networkx as nx


class ALU:
  # ruijief: 
  # an ALU object represents a physical ALU. We will use this class
  # to represent a node in the dependency graph we feed to ILP,
  # and different ALUs will have different edges (which model ILP dependencies).
  # ALU(id, stmt, lineno, wire)
  #  id: the ID of the ALU, usually numbered [1...N] where N is the number of ALUs.
  #  stmt: The statement of the 
  def __init__(self, id, stmt, lineno, wire=False):
    self.id = id
    self.stmt = stmt
    self.lineno = lineno
    self.wire = wire
    self.process_stmt()

  def process_stmt(self):
    # parses a statement into a wire. 
    lexer = lex.lex(module=lexerRules)
    lexer.input(self.stmt)
    if not self.wire:
      args_st = False
      arg_tokens = []
      for tok in lexer:
        if tok.type == 'RPAREN':
          args_st = False

        if args_st:
          arg_tokens.append(tok)

        if tok.type == 'LPAREN':
          args_st = True

      self.opcode = arg_tokens[0].value  # first argument is ALU opcode
      input_tokens = arg_tokens[1:-1]
      self.inputs = [t.value for t in input_tokens]
      self.output = arg_tokens[-1].value  # last argument is the output variable

    else:
      toks = []
      for tok in lexer:
        toks.append(tok)
      assert (toks[0].type == 'ID')
      output = toks[0].value
      assert (toks[2].type == 'ID')
      self.inputs = [toks[2].value]
      self.output = output

  def print(self):
    if not self.wire:
      print("{} = ALU(opcode={}, inputs={})".format(self.output, self.opcode, ", ".join(self.inputs), ))
    else:
      print("{} = {}".format(self.output, self.inputs[0]))


class SketchOutputProcessor:
  def __init__(self):
    self.dependencies = {}  # key: alu, value: list of alus depending on key
    self.rev_dependencies = {}  # key: alu, value: list of alus that key depends on
    self.alu_outputs = {}  # key: output variable, value: alu stmt (string)
    self.alus = []
    self.alu_dep_graph = nx.DiGraph()
    self.alu_id = 0

  def process_output(self, input_file, output):
    f = open(input_file, "r")

    l = f.readline()
    while not l.startswith("void sketch"):
      l = f.readline()

    # l is "void sketch..."
    l = f.readline()

    lineno = 0
    lhs_assert = ""
    # as long as we don't encounter the end of `void sketch` function,
    # continue lexing each line using lexerRules.
    while not l.startswith("}"):
      lexer = lex.lex(module=lexerRules)
      lexer.input(l)
      l_toks = []
      # lex everything into a list of tokens.
      for tok in lexer:
        l_toks.append(tok)

      # if len(l_toks) == 4 and 'ASSIGN' in [tok.type for tok in l_toks]: # assignment stmt
      # 	lhs_tok = l_toks[1]
      # 	assert(lhs_tok.type == 'ID')
      # 	alu_output = lhs_tok.value
      print(l_toks)
      if l_toks[0].type == 'RBRACE':
        break

      elif l_toks[0].type == 'ASSERT':
        assert (l_toks[2].type == 'ID')
        lhs_assert = l_toks[2].value

      elif l_toks[0].type == 'ID' and l_toks[0].value.startswith("alu"):  # alu stmt
        alu = ALU(self.alu_id, l, lineno)
        self.alu_id += 1
        self.alus.append(alu)
        self.alu_outputs[alu.output] = alu
        self.dependencies[alu] = []
        self.rev_dependencies[alu] = []

      l = f.readline()
      lineno += 1

    if len(self.alus) > 0:  # not just an assignment
      # rename last ALU's output
      self.alus[-1].output = output
      self.alu_outputs[alu.output] = alu
    else:
      stmt = "{} = {}".format(output, lhs_assert)
      alu = ALU(self.alu_id, stmt, lineno, True)
      self.alu_id += 1
      self.alus.append(alu)
      self.alu_outputs[alu.output] = alu
      self.dependencies[alu] = []
      self.rev_dependencies[alu] = []

    self.find_dependencies()

  # def process_stateful_output(self, input_file, output):

  # ruijief: 
  # find_dependencies finds dependencies (i.e. directed edges) between ALUs, which are nodes
  # in the ILP dependency graph.
  def find_dependencies(self):
    for alu1 in self.alus:
      for alu2 in self.alus:
        if alu2 != alu1 and alu1.output in alu2.inputs and alu1.lineno < alu2.lineno:  # RAW
          self.dependencies[alu1].append(alu2)
          self.rev_dependencies[alu2].append(alu1)

    for alu in self.alus:
      self.alu_dep_graph.add_node(alu)

    for alu in self.alus:
      self.alu_dep_graph.add_edges_from([(alu, alu1) for alu1 in self.dependencies[alu]])

  # ruijief:
  # TODO: call the ILP_Gurobi.py solver to do scheduling
  def schedule(self):
    self.level = {}  # key: node, value: level
    self.schedule = {}  # key: stage number, value: list of alus in that stage

    for u in nx.topological_sort(self.alu_dep_graph):
      deps = self.rev_dependencies[u]
      if len(deps) == 0:
        self.level[u] = 0
        if 0 not in self.schedule:
          self.schedule[0] = [u]
        else:
          self.schedule[0].append(u)

      else:
        deps_levels = [self.level[v] for v in deps]  # all v in deps will occur before u in the topological sort
        max_dep_level = max(deps_levels)
        self.level[u] = max_dep_level + 1
        if (max_dep_level + 1) not in self.schedule:
          self.schedule[max_dep_level + 1] = [u]
        else:
          self.schedule[max_dep_level + 1].append(u)

    for stage, alus in self.schedule.items():
      print("stage:", stage)
      for alu in alus:
        alu.print()


if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: <input file> <output name>")
    exit(1)

  input_file = sys.argv[1]
  output = sys.argv[2]
  processor = SketchOutputProcessor()
  processor.process_output(input_file, output)
  processor.schedule()
