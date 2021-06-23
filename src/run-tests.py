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


class CodeGen:
  def __init__(self, filename, outputfilename, fdfd):
    self.var_types = {}  # key: variable, value: type
    self.stmt_map = {}  # key: lhs var, value: list of assignment statements
    self.tmp_vars = {}  # key: tmp var, value: rhs
    self.mp_vars_rev = {}  # reverse map of tmp_vars
    self.rhs_map = {}  # rhs, lhs
    self.state_variables = set()
    self.filename = filename
    self.outputfilename = outputfilename
    self.tmp_cnt = 0
    self.get_type_info(fdfd)

  def get_type_info(self, fdfd):
    state_var = False

    line = fdfd.readline()
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

      line = fdfd.readline()



if __name__ == "__main__":
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument("out_folder", help="test output folder")
  arg_parser.add_argument('out_file', help='testing statistics file')
  args = arg_parser.parse_args()
  out_folder = args.out_folder 
  log_file = args.out_file
  tests = ['blue_decrease', 'blue_increase', 'flowlets', 'marple_tcp_nmo', 'marple_new_flow', 'sampling']
  log_fd = open(out_folder + '/' + log_file, 'w')
  for test_name in tests: 
    print('-------------------------- running test ', test_name, ' -----------------------------------')
    start = time.time()
    filename = test_name + '.in'
    output_folder_name = out_folder + '/' + '_' + test_name + '_out'
    p4outputname = out_folder + '/' + test_name + '.p4'
    codeGen = None 
    dep_graph_obj = None
    synth_obj = None
    with open(filename, "r") as f:
      codeGen = CodeGen(filename, output_folder_name, f)
      print('STATE VARIABLES: ----------------- ', codeGen.state_variables)
      dep_graph_obj = depG.DependencyGraph(filename, codeGen.state_variables, codeGen.var_types)
      synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, \
                                    dep_graph_obj.scc_graph, dep_graph_obj.stateful_nodes, output_folder_name, p4outputname)
      print('----- starting ILP Gurobi -----')
      ilp_table = synth_obj.synth_output_processor.to_ILP_TableInfo(table_name = 'T0')
      print("# alus: = ", ilp_table.get_num_alus())
      ilp_output = ilp_table.ILP() 
      import p4_codegen 
      codegen = p4_codegen.P4Codegen(ilp_table, ilp_output, "test")
      codegen.generate_p4_output('tofino_p4.j2', p4outputname)
    end = time.time()
    
    print('---------------------------- finished testing ', test_name, '; statistics  ---------------------')
    print("Time taken: {} s".format(end - start))
    print('Num ALU stages: ', ilp_output.find_number_of_stages())
    print('Num ALUs: ', ilp_table.get_num_alus())
    print('------------------------------------------------------------------------------------------------')

    log_fd.write('---------------------------- finished testing '+ test_name+ '; statistics  ---------------------\n')
    log_fd.write("Time taken: {} s\n".format(end - start))
    log_fd.write('Num ALU stages: ' + str(ilp_output.find_number_of_stages()) + '\n')
    log_fd.write('Num ALUs: ' + str(ilp_table.get_num_alus()) + '\n')
    log_fd.write('------------------------------------------------------------------------------------------------\n')
