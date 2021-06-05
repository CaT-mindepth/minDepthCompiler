from os import confstr
import sys
import lexerRules
import ply.lex as lex
import networkx as nx


class TernaryExpression(lex.LexToken):
  def __init__(self):
    self.condition = None 
    self.yes = None 
    self.no = None 
    self._placeholder()
  
  def __init__(self, cond, y, n):
    self.condition = cond 
    self.yes = y 
    self.no = n 
    self._placeholder()

  def fix(self):
    self.type = "TERNARY"
    self.value = str(self)

  def _placeholder(self):
    self.lineno = 0  # placeholder
    self.lexpos = 0  # placeholder
  
  # TODO: make more efficient
  def __str__(self):
    assert self.condition != None 
    assert self.yes != None 
    assert self.no != None 
    s = "( "
    for tok in self.condition:
      s += tok.value + " "
    s += ") ? ( "
    for tok in self.yes:
      s += tok.value + " "
    s += ") : ( "
    for tok in self.no:
      s += tok.value + " "
    s += ")"
    return s 

class SALU(object):
  # ruijief:
  # this represents a Stateful ALU object.
  
  def __init__(self, id, alu_filename, metadata_lo_name, metadata_hi_name, 
                register_lo_0_name, register_hi_1_name, out_name):
    self.id = id 
    self.alu_filename = alu_filename
    self.salu_arguments = ['metadata_lo', 'metadata_hi', 'register_lo_0', 'register_hi_1', '_out']
    self.demangle_list = ['condition_hi',
            'condition_lo',
            'update_lo_1_predicate',
            'update_lo_1_value',
            'update_lo_2_predicate',
            'update_lo_2_value',
            'update_hi_1_predicate',
            'update_hi_1_value',
            'update_hi_2_predicate',
            'update_hi_2_value',
            'output_value',
            'output_dst']
    self.var_expressions = {} # dict for storing expressions of synthesized variables.
    self.salu_arguments_mapping = {
      'metadata_lo': metadata_lo_name,
      'metadata_hi': metadata_hi_name,
      'register_lo': register_lo_0_name,
      'register_hi_1_name': register_hi_1_name,
      '_out': out_name 
    }
    self.process_salu_function()
    for k, v in self.var_expressions: 
      self.var_expressions[k] = list(map(lambda tok: tok if not (tok.value in self.salu_arguments) 
        else self.new_token(tok.type, tok.value, tok.lineno, tok.lexpos)))
      

  """
    This helper method helps construct a new PLY LexToken object.
  """
  def new_token(self, type, value, lineno=0, lexpos=0):
    t = lex.LexToken()
    t.value = value 
    t.type = type 
    t.lineno = lineno 
    t.lexpos = lexpos 
    return t 
  
  """
    This helper method below helps us determine whether we've encountered
    a lhs variable in Sketch that's among the synthesized variables.
  """
  def demangle(self, var_name):
    for x in self.demangle_list:
      if var_name.startswith(x):
        return True, x 
    return False, None 
"""
  the methods below implemenet a ballpark visitor pattern on the source code lines
  to find synthesized expressions for SALU variables in the salu(...) function in Sketch.
"""
def process_salu_function_ifelse_stmt_body(self, lexer, fd, curr_ter, curr_ter_lhs, ifelse_type):
  l = fd.readline() # eat the '{'
  l = fd.readline() 
  nested_term = None 
  while not l.startswith('}'):
    lexer.input(l)
    # fill in the "yes" field in curr_ter 
    lexer.input(l)
    toks = [tok for tok in lexer] 
    if toks[0].type == 'ID':
      # if type is ID, then first position must be curr_ter_lhs
      # this must be an assignment statement.
      assert toks[0].value == curr_ter_lhs 
      assert toks[1].type == 'ASSIGN'
      if ifelse_type == 'IF':
        curr_ter.yes = toks[2:]
      else: # is else
        curr_ter.no = toks[2:]

    elif toks[0].type == 'IF':
      # do recursion
      # IF LBRACE ... RBRACE
      assert toks[1].type == 'LBRACE'
      assert toks[-1].type == 'RBRACE'
      nested_term = TernaryExpression(toks[2:-1], None, None) 
      # recursively process if_stmt body
      # note: curr_ter_lhs remains invariant in nested scopes
      self.process_salu_function_ifelse_stmt_body(lexer, fd, nested_term, curr_ter_lhs, 'IF')
      
    elif toks[0].type == 'ELSE':
      # recursively process else.
      self.process_salu_function_ifelse_stmt_body(lexer, fd, nested_term, curr_ter_lhs, 'ELSE')
      nested_term.fix() 
      if ifelse_type == 'IF':
        curr_ter.yes = nested_term 
      else:
        curr_ter.no = nested_term 
    l = fd.readline()
  return curr_ter

def process_salu_function(self):
  with open(self.alu_filename) as f: 
    l = f.readline() 
    # navigate to the line 'void salu'
    while not l.startswith('void salu'):
      l = f.readline() 
    l = f.readline() # eat the '{' symbol
    l = f.readline() # first line in function block 
    lexer = lex.lex(module=lexerRules)
    curr_ter = None 
    curr_ter_lhs = 'register_hi'
    while not l.startswith('}'): # this right bracket denotes the termination of the salu function. We recursively visit each stmt block inside this.
      lexer.input(l)
      toks = []
      for tok in lexer:
        toks.append(tok)
      if toks[0].type == 'ID':
        is_lhs_good, demangled = self.demangle(toks[0].value) 
        if is_lhs_good: # found a var whose expression we need to keep track of.
          assert(toks[1].type == 'ASSIGN') # lhs '=' rhs
          self.var_expressions[demangled] = toks[2:]

      elif (toks[0].type == 'IF'):
        # IF LBRACE ... RBRACE 
        assert toks[1].type == 'LBRACE'
        assert toks[-1].type == 'RBRACE' 
        curr_ter = TernaryExpression(toks[2:-1], None, None) 
        # <stmt body>
        curr_ter = self.process_salu_function_ifelse_stmt_body(lexer, f, curr_ter, curr_ter_lhs, "IF")

      elif toks[0].type == 'ELSE':
        curr_ter = self.process_salu_function_ifelse_stmt_body(lexer, f, curr_ter, curr_ter_lhs, "ELSE")
        curr_ter.fix() 
        # update corresponding lhs in the state dict.
        self.var_expressions[curr_ter_lhs] = curr_ter # assign curr_ter_lhs to curr_ter
        if curr_ter_lhs == 'register_hi':
          curr_ter_lhs = 'register_lo' # register_lo always processed after register_hi

      elif toks[0].type == 'RBRACKET':
        break 
      # read the next line.
      l = f.readline()


""" self.alu_visitor = TofinoStatefulAluVisitor(self.alu_filename, None, None,
                 operand0, operand1)
                
            'condition_hi',
            'condition_lo',
            'update_lo_1_predicate',
            'update_lo_1_value',
            'update_lo_2_predicate',
            'update_lo_2_value',
            'update_hi_1_predicate',
            'update_hi_1_value',
            'update_hi_2_predicate',
            'update_hi_2_value',
            'output_value',
            'output_dst'"""


class StatefulSketchOutputProcessor(object):
  def __init__(self):
    self.dependencies = {}  # key: alu, value: list of alus depending on key
    self.rev_dependencies = {}  # key: alu, value: list of alus that key depends on
    self.alu_outputs = {}  # key: output variable, value: alu stmt (string)
    self.alus = []
    self.alu_dep_graph = nx.DiGraph()
    self.alu_id = 0

  def process_outputs(self, input_files, output):
    for input_file in input_files:
      self.process_single_output(input_file, output)

  def process_single_output(self, input_file, output):
    f = open(input_file, "r")

    l = f.readline()
    while not l.startswith("void sketch"):
      l = f.readline()
    l = f.readline() 
    # l is "void sketch..."
    l = f.readline()

    lhs_assert = ""
    # as long as we don't encounter the end of `void sketch` function,
    # continue lexing each line using lexerRules.
    while not l.startswith("}"):
      lexer = lex.lex(module=lexerRules)
      lexer.input(l)
      l_toks = []
      # lex everything on this line l into a list of tokens.
      for tok in lexer:
        l_toks.append(tok)

      if l_toks[0].type == 'RBRACE':
        break

      elif l_toks[0].type == 'ASSERT':
        assert (l_toks[2].type == 'ID')
        lhs_assert = l_toks[2].value

      elif l_toks[0].type == 'ID' and l_toks[0].value.startswith("salu"):  # alu stmt
        #(self, id, alu_filename, metadata_lo_name, metadata_hi_name, 
        #        register_lo_0_name, register_hi_1_name, out_name):
        alu = SALU(self.alu_id, input_file, l_toks[2].value, 
                    l_toks[3].value, l_toks[4].value, l_toks[5].value, lhs_assert)
        self.alu_id += 1
        self.alus.append(alu)
        self.alu_outputs[alu.output] = alu
        self.dependencies[alu] = []
        self.rev_dependencies[alu] = []

      l = f.readline()

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

  # ruijief: 
  # find_dependencies finds dependencies (i.e. directed edges) between ALUs, which are nodes
  # in the ILP dependency graph.
  def find_dependencies(self):
    for alu1 in self.alus:
      for alu2 in self.alus:
        if alu2 != alu1 and alu1.output in alu2.inputs: #and alu1.lineno < alu2.lineno:  # RAW
          self.dependencies[alu1].append(alu2)
          self.rev_dependencies[alu2].append(alu1)

    for alu in self.alus:
      self.alu_dep_graph.add_node(alu)

    for alu in self.alus:
      self.alu_dep_graph.add_edges_from([(alu, alu1) for alu1 in self.dependencies[alu]])

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
    pass

"""
if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: <input file> <output name>")
    exit(1)

  input_file = sys.argv[1]
  output = sys.argv[2]
  processor = SketchOutputProcessor()
  processor.process_output(input_file, output)
  processor.schedule()
"""