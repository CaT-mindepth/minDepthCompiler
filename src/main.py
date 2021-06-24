import argparse
import ply.lex as lex
import lexerRules
import time
import dependencyGraph as depG
import synthesis
import ILP_Gurobi
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


class CodeGen:


  def __init__(self, filename, outputfilename, f):

    self.var_types = {}  # key: variable, value: type
    self.stmt_map = {}  # key: lhs var, value: list of assignment statements
    self.tmp_vars = {}  # key: tmp var, value: rhs
    self.tmp_vars_rev = {}  # reverse map of tmp_vars
    self.rhs_map = {}  # rhs, lhs
    self.state_variables = set()

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
  arg_parser.add_argument("--input", nargs='+', dest='input', help="input file (preprocessed Domino program)", required=True)
  arg_parser.add_argument("sketch", help="Sketch files folder")
  arg_parser.add_argument('output', help='P4 output location')
  arg_parser.add_argument('--table-deps', dest='table_deps', help='table dependencies file')
  arg_parser.add_argument('--table-action-mapping', dest='table_action_map', help='table action mapping')
  args = arg_parser.parse_args()

  filename = args.input
  outputfilename = args.sketch
  p4outputname = args.output

  table_deps_file = args.table_deps 
  table_action_map = args.table_action_map

  print('filenames: ', filename)
  print('table deps file: ', table_deps_file)
  print('table action mapping: ', table_action_map)
  print('output folder: ', outputfilename)
  print('output p4 program: ', p4outputname)

  start = time.time()

  # rename tables to T0, T1, ..., Tn
  table_num = 0 
  tables = set()
  table_name_to_ILP_table_name = {}
  ILP_table_name_to_action_map = {}
  ILP_table_name_deps = {}

  # parse table->action mapping
  with open(table_action_map) as fd:
    table_actions = fd.readlines() 
    for line in table_actions:
      table_action_dep = line.split(' ')
      table_name = table_action_dep[0].strip()
      action_name = table_action_dep[1].strip()
      ILP_table_name = None
      if not (table_name in tables):
        tables.add(table_name)
        ILP_table_name = 'T' + str(table_num)        
        table_name_to_ILP_table_name[table_name] = ILP_table_name
        table_num+=1
        ILP_table_name_to_action_map[ILP_table_name] = [ action_name ] 
      else:
        ILP_table_name = table_name_to_ILP_table_name[table_name]
        ILP_table_name_to_action_map[ILP_table_name].append(action_name)
      print(' - mapping table ', table_name, ' to ', ILP_table_name, ', it has action ', action_name)

  print(table_name_to_ILP_table_name)
  print(ILP_table_name_to_action_map)

  # parse table dependencies.
  # there are 4 types of dependencies: Match, Action, Successor, Reverse
  ILP_table_name_deps['Match'] = []
  ILP_table_name_deps['Action'] = []
  ILP_table_name_deps['Successor'] = []
  ILP_table_name_deps['Reverse'] = []
  with open(table_deps_file) as fd: 
    dep_lines = fd.readlines() 
    for line in dep_lines:
      toks = list(map(lambda x: x.strip(), line.split(' ')))
      if toks[0] != 'Match' and toks[0] != 'Action' and toks[0] != 'Successor' and toks[0] != 'Reverse':
        print('Error: invalid dependency type @ ', line)
      ILP_table_name_deps[toks[0]].append((toks[1], toks[2]))
  print(' ------- table dependencies ------ ')
  print(ILP_table_name_deps)
  print(' --------------------------------- ')
  ILP_dep_obj = ILP_Gurobi.ILP_TableDeps(ILP_table_name_deps['Match'], ILP_table_name_deps['Action'], ILP_table_name_deps['Successor'], \
    ILP_table_name_deps['Reverse'])
  codeGens = []
  depGraphs = []
  synthObjs = []
  for file in filename: 
    print(' compiling action file ', file)
    with open(file, "r") as f:
      codeGen = CodeGen(file, outputfilename, f)
      dep_graph_obj = depG.DependencyGraph(file, codeGen.state_variables, codeGen.var_types)
      synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, \
                                    dep_graph_obj.scc_graph, dep_graph_obj.stateful_nodes, outputfilename, p4outputname)
      codeGens.append(codeGen)
      depGraphs.append(dep_graph_obj)
      synthObjs.append(synthObjs)
  exit(0)

  # ILP
  # self.synth_output_processor.schedule()
	# TODO here
  """
  print('----- starting ILP Gurobi -----')
	ilp_table = self.synth_output_processor.to_ILP_TableInfo(table_name = 'T0')
	print("# alus: = ", ilp_table.get_num_alus())
	ilp_output = ilp_table.ILP() 
	import p4_codegen 
	codegen = p4_codegen.P4Codegen(ilp_table, ilp_output, "test")
	codegen.generate_p4_output('tofino_p4.j2', p4_output_name)
  end = time.time()
  print("Time taken: {} s".format(end - start))
"""