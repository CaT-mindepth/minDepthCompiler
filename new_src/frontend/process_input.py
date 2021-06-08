import logging
from .. import pass_manager

class ProcessInput(pass_manager.Pass):
  var_types = {}  # key: variable, value: type
  stmt_map = {}  # key: lhs var, value: list of assignment statements
  tmp_vars = {}  # key: tmp var, value: rhs
  tmp_vars_rev = {}  # reverse map of tmp_vars
  rhs_map = {}  # rhs, lhs
  state_variables = set()

  def __init__(self, filename, outputfilename):
    self.filename = filename
    self.outputfilename = outputfilename
    self.tmp_cnt = 0

    self.get_type_info()

  def process_expr(self, rhs_expr, lhs, f_out, rhs_tokens, line_no=0):
    lhs_type = self.var_types[lhs]

    if lhs_type == "int" and not has_rel_op(rhs_expr):  # arith expr
      print("arith expr")
      rhs_expr = simplify_arith(rhs_expr)
      three_addr_code = self.get_min_depth_expr(rhs_expr, lhs, line_no)
      self.write_code_to_file(three_addr_code, False, f_out)

    elif has_rel_op(rhs_expr) and not has_bool_op(rhs_expr):  # pure relational expr
      print("pure rel expr")
      rhs_expr = simplify_rel(rhs_expr)
      three_addr_code = self.get_min_depth_expr(rhs_expr, lhs, line_no)
      self.write_code_to_file(three_addr_code, False, f_out)

    elif lhs_type == "bit" and has_only_inequality(rhs_expr) and has_bool_op(rhs_expr):
      print("rel + bool expr with only !=")
      three_addr_code = self.get_min_depth_expr(rhs_expr, lhs, line_no)
      self.write_code_to_file(three_addr_code, False, f_out)

    elif lhs_type == "bit" and has_rel_op(rhs_expr) and has_bool_op(rhs_expr):  # mixed relational Boolean expr
      print("rel + bool expr")
      bool_expr, bool_var_map, bool_var_rev_map = self.parse_rel_bool_expr(rhs_expr)
      print("bool expr:", bool_expr)
      bool_expr = simplify_bool(bool_expr)

      three_addr_code = self.get_min_depth_expr(bool_expr, lhs, line_no)
      self.write_code_to_file(three_addr_code, True, f_out, bool_var_map, bool_var_rev_map)

    elif lhs_type == "bit" and not has_rel_op(rhs_expr) and has_bool_op(rhs_expr):  # pure Boolean expr
      print("pure bool expr")
      rhs_expr = simplify_bool(rhs_expr)
      three_addr_code = self.get_min_depth_expr(rhs_expr, lhs, line_no)
      self.write_code_to_file(three_addr_code, False, f_out)

    else:
      print("Unknown expression type")
      assert (False)

  def process_line(self, line, line_no, f_out):
    lexer = lex.lex(module=lexerRules)
    lexer.input(line)
    rhs_variables = set()
    rhs_toks = []
    assign_seen = False
    tok_cnt = 0

    for tok in lexer:
      # print(tok)
      if assign_seen:
        rhs_toks.append(tok)
        if tok.type == 'ID':
          rhs_variables.add(tok.value)

      if tok.type == 'ASSIGN':
        assign_seen = True

      if not assign_seen:
        lhs = tok.value

      tok_cnt += 1

    if lhs not in self.stmt_map:
      self.stmt_map[lhs] = [(line, rhs_variables, line_no, rhs_toks)]
    else:
      self.stmt_map[lhs].append((line, rhs_variables, line_no, rhs_toks))

    rhs_expr = " ".join([tok.value for tok in rhs_toks])
    rhs_expr = rhs_expr.replace("( ", "(")
    rhs_expr = rhs_expr.replace(" )", ")")

    self.rhs_map[rhs_expr] = lhs
    self.process_expr(rhs_expr, lhs, f_out, rhs_toks, line_no)

  def process_input(self, f, f_out):
    # lines = f.readlines()
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

    line = f.readline()  # line after declarations end
    # f_out.write("# declarations end\n")

    line_no = 1
    while line:
      print("\nline:", line)
      if ('?' in line) and (':' in line):
        print(line, "ite statement, no simplification needed")
        f_out.write(line)
      elif ("[" in line) or ("]" in line):
        print(line, "read/write flank, no simplification needed")
        f_out.write(line)
      else:
        self.process_line(line, line_no, f_out)

      line_no += 1
      line = f.readline()

  def get_type_info(self):
    # lines = f.readlines()
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
