import argparse
import ply.lex as lex
import lexerRules
import time
import dependencyGraph as depG
import synthesis

def tokenize_expr(expr):
  toks = []
  variables = set()
  lexer = lex.lex(module=lexerRules)
  lexer.input(expr)
  for tok in lexer:
    toks.append(tok)
    if tok.type == "ID":
      variables.add(tok.value)
  return (toks, variables)


class codeGen:
  var_types = {}  # key: variable, value: type
  stmt_map = {}  # key: lhs var, value: list of assignment statements
  tmp_vars = {}  # key: tmp var, value: rhs
  tmp_vars_rev = {}  # reverse map of tmp_vars
  rhs_map = {}  # rhs, lhs
  state_variables = set()

  def __init__(self, filename, outputfilename, f):
    self.filename = filename
    self.outputfilename = outputfilename
    self.tmp_cnt = 0

    self.get_type_info(f)

  def get_type_info(self, f):
    decls_end = False
    line_no = 0
    state_var = False

    line = f.readline()
    while line != "# declarations end\n":
      # store type information
      if line == "# state variables start\n":
        state_var = True
      elif line == "# state variables end\n":
        state_var = False
      else:
        line = line.rstrip()
        line = line.replace(";", "")
        toks = line.split(" ")
        assert (len(toks) == 2)
        var_name = toks[1].rstrip()
        self.var_types[var_name] = toks[0]

        if state_var:  # state variable. TODO: make this more general
          self.state_variables.add(var_name)

      line = f.readline()


if __name__ == "__main__":
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument("input", help="input file (preprocessed Domino program)")
  arg_parser.add_argument("output", help="output file")
  arg_parser.add_argument("--stages", help="number of pipeline stages", type=int)
  arg_parser.add_argument("--ALUs", help="number of ALUs per stage", type=int)

  args = arg_parser.parse_args()

  filename = args.input
  outputfilename = args.output
  max_stages = args.stages
  max_alus = args.ALUs

  start = time.time()


  with open(filename, "r") as f:
    codeGen = codeGen(filename, outputfilename, f)

  dep_graph_obj = depG.DependencyGraph(filename, codeGen.state_variables, codeGen.var_types)
  synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, \
                                    dep_graph_obj.scc_graph, dep_graph_obj.stateful_nodes, outputfilename)

  

  end = time.time()
  print("Time taken: {} s".format(end - start))
