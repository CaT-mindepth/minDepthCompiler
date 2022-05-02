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


# tofino_stateless_grammar = 'grammars/stateless_tofino.sk'
tofino_stateless_grammar = 'grammars/stateless_tofino_new.sk'
tofino_stateful_grammar = 'grammars/stateful_tofino.sk'


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
    self.pkt_vars = set()
    self.get_type_info(f)

  def get_type_info(self, f):
    decls_end = False
    line_no = 0
    state_var = False
    pkt_var = False
    line = f.readline()
    while line != "# declarations end\n":
      # store type information
      if line == "# state variables start\n":
        state_var = True
      elif line == "# state variables end\n":
        state_var = False
      elif line == "# packet vars start\n":
        pkt_var = True
      elif pkt_var:
        line = line.rstrip()
        self.pkt_vars.add(line)
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
  arg_parser.add_argument("sketch", help="Sketch files folder")
  arg_parser.add_argument('output', help='P4 output location')
  arg_parser.add_argument("--stages", help="number of pipeline stages", type=int)
  arg_parser.add_argument("--ALUs", help="number of ALUs per stage", type=int)
  arg_parser.add_argument("--predPack", help="enable_predecessor_packing", action="store_true")
  arg_parser.add_argument('--eval', help="evaluation mode", action="store_true")
  args = arg_parser.parse_args()

  filename = args.input
  outputfilename = args.sketch
  p4outputname = args.output
  max_stages = args.stages
  max_alus = args.ALUs

  start = time.time()

  print('enabling predecessor packing? ', args.predPack)
  with open(filename, "r") as f:
    codeGen = codeGen(filename, outputfilename, f)

  dep_graph_obj = depG.DependencyGraph(filename, codeGen.state_variables, codeGen.var_types, stateful_grammar="tofino", eval = args.eval)


  synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, codeGen.pkt_vars,  dep_graph_obj.PIs,\
                                    dep_graph_obj.scc_graph, dep_graph_obj.read_write_flanks, dep_graph_obj.stateful_nodes,
                                     outputfilename, p4outputname, enableMerging = args.predPack, \
                                     is_tofino = True, stateless_path = 'tofino', 
                                     stateful_path='tofino', eval = args.eval)


  
  # ILP
  # self.synth_output_processor.schedule()
	# TODO here
  print('----- starting ILP Gurobi -----')
  ilp_table = synth_obj.synth_output_processor.to_ILP_TableInfo(table_name = 'T0')
  print("# alus: = ", ilp_table.get_num_alus())
  ilp_output = ilp_table.ILP() 
  import p4_codegen 
  codegen = p4_codegen.P4Codegen(ilp_table, ilp_output, "test")
  codegen.generate_p4_output('tofino_p4.j2', p4outputname)
  #codegen.generate_json_output('tofino_p4.j2', p4outputname)
  

  

  end = time.time()
  print("Time taken: {} s".format(end - start))

