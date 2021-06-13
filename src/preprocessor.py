import sys
import sympy
import lexerRulesOrig
import ply.lex as lex


class Preprocessor:
  def __init__(self, input_file, output_filename):
    self.f = input_file
    self.outfilename = output_filename
    self.macros = {}  # key: macro name, value: macro value
    self.packet_variables = []  # list of packet variables
    self.state_variables = []
    self.pkt_state_map = {}  # key: new temp pkt var, value: state variable
    self.state_pkt_map = {}  # key: state var, value: pkt field
    self.var_type = {}
    self.var_idx = {}  # key: variable name, value: index for SSA
    self.func_lines = []
    self.stmts = {}  # key: lhs, value: rhs
    self.final_stmts = []
    self.cond_stack = []  # stack keeping track of control flow
    self.cond_stmts = {}  # key: branch var, value: dictionary, indexed by lhs
    self.cond = {}  # key: branch var, value: condition
    self.cond_idx = {}  # idx of vars before cond

    self.lexer = lex.lex(module=lexerRulesOrig)

    self.pkt_name = ""
    self.branch_var_prefix = "br_tmp"
    self.branch_var_cnt = 0  # counter for temporary variables for branch elimination

    self.process_input()

  def simplify_arith(self, expr):
    print("simplifying arith expression: " + expr)
    expr = sympy.sstr(sympy.sympify(expr))
    print("to ", expr)
    return expr

  def tokenize(self, l):
    self.lexer.input(l)

    toks = []
    while True:
      tok = self.lexer.token()
      if not tok:
        break
      else:
        toks.append(tok)

    return toks

  def is_array_var(self, t):
    return ("[" in t)

  def process_state_var(self, t, no_idx=False):
    t1 = ""
    idx = 0
    if t in self.state_pkt_map:
      t1 = self.state_pkt_map[t]
      assert (t1 in self.var_idx)
      idx = self.var_idx[t1]
    else:
      t1 = self.pkt_name + "_" + t

      self.var_idx[t1] = 0
      self.var_type[t1] = self.var_type[t]
      read_flank = "{} = {}".format(t1 + str(idx), t)
      self.stmts[t1 + str(idx)] = t
      self.final_stmts.append(read_flank)  # read flank
      self.pkt_state_map[t1] = t
      self.state_pkt_map[t] = t1

    if no_idx:
      return t1
    else:
      return t1 + str(idx)

  def process_array_state_var(self, t, no_idx=False):
    t1 = ""
    idx = 0

    array_name = t[:t.find("[")]
    array_index = t[t.find("[") + 1: t.find("]")]
    array_index = self.process_rhs(array_index, self.var_type[array_name])
    t = array_name + "[" + array_index + "]"
    print("new t", t)

    if t in self.state_pkt_map:
      t1 = self.state_pkt_map[t]
      assert (t1 in self.var_idx)
      idx = self.var_idx[t1]
    else:
      t1 = self.pkt_name + "_" + array_name + "_" + array_index + "_"
      self.var_idx[t1] = 0
      self.var_type[t1] = self.var_type[array_name]
      read_flank = "{} = {}".format(t1 + str(idx), t)
      self.stmts[t1 + str(idx)] = t
      self.final_stmts.append(read_flank)
      self.pkt_state_map[t1] = t
      self.state_pkt_map[t] = t1

    if no_idx:
      return t1
    else:
      return t1 + str(idx)

  def isStateVariable(self, var):
    return (var in self.state_variables) or (var[:var.find("[")] in self.state_variables)

  def process_lhs(self, lhs, no_idx=False):
    lhs = lhs.strip()
    pkt_field = lhs
    if lhs in self.state_variables or lhs[:lhs.find("[")] in self.state_variables:

      if self.is_array_var(lhs):  # array var
        pkt_field = self.process_array_state_var(lhs, no_idx)
      else:
        pkt_field = self.process_state_var(lhs, no_idx)

    return pkt_field

  def process_rhs(self, rhs, expr_type):
    toks = self.tokenize(rhs)

    found_var = False

    for tok in toks:
      t = tok.value
      # print(tok)
      if tok.type == 'ID':
        if t in self.macros:  # macro
          rhs = rhs.replace(t, self.macros[t])

        else:  # variable
          found_var = True
          pkt_field = ""
          if t in self.state_variables or t[:t.find("[")] in self.state_variables:

            if self.is_array_var(t):  # array var
              pkt_field = self.process_array_state_var(t)
            else:
              pkt_field = self.process_state_var(t)

            rhs = rhs.replace(t, pkt_field)

          else:
            idx = self.var_idx[t]
            rhs = rhs.replace(t, t + str(idx))

    if not found_var and expr_type == "int":  # constant arithmetic expression
      rhs = self.simplify_arith(rhs)

    return rhs

  def process_assgn(self, l):
    print("process_assgn")
    toks = self.tokenize(l)
    assert (toks[1].type == "ASSIGN")
    lhs = toks[0].value
    rhs = " ".join([t.value for t in toks[2:]])

    print("lhs", lhs, "rhs", rhs)
    if lhs == rhs:
      pass
    else:
      lhs = self.process_lhs(lhs, no_idx=True)
      lhs_type = self.var_type[lhs]
      rhs = self.process_rhs(rhs, lhs_type)

      if lhs != rhs:
        var_id = self.var_idx[lhs]
        self.var_idx[lhs] = var_id + 1
        lhs = lhs + str(var_id + 1)

        self.stmts[lhs] = rhs
        self.final_stmts.append("{} = {}".format(lhs, rhs))

  def isSingleVariable(self, expr):  # return true if expr contains a single variable that isn't a state variable
    # (We don't want to delete read flanks)
    toks = self.tokenize(expr)
    return (len(toks) == 1) and (toks[0].type == "ID") and (not self.isStateVariable(toks[0].value))

  def selector_simple_rhs(self, var):
    # print(self.stmts)

    if (var in self.stmts) and self.stmts[var].isdigit():
      self.final_stmts.remove("{} = {}".format(var, self.stmts[var]))  # delete
      return self.stmts[var]  # replace by rhs if rhs is constant
    elif (var in self.stmts) and self.isSingleVariable(self.stmts[var]):
      self.final_stmts.remove("{} = {}".format(var, self.stmts[var]))  # delete
      return self.tokenize(self.stmts[var])[0].value
    else:
      return var

  def get_cond_idx(self, var):
    if not var in self.cond_idx:
      self.cond_idx[var] = 0

    return self.cond_idx[var]

  def selector_stmts(self, cond_lhs):  # TODO: optimize for if-else (use only one phi node)
    print("selector stmts")
    print(self.cond_stmts)
    print("cond_lhs", cond_lhs)
    for var, var_data in self.cond_stmts[cond_lhs].items():
      print("var", var)
      t_var = var + str(var_data["T"])
      t_var = self.selector_simple_rhs(t_var)

      f_var = var + str(var_data["O"])
      f_var = self.selector_simple_rhs(f_var)

      print("t_var", t_var, "f_var", f_var)
      self.var_idx[var] += 1
      sel_lhs = var + str(self.var_idx[var])
      sel_rhs = "{} ? {} : {}".format(cond_lhs, t_var, f_var)

      self.stmts[sel_lhs] = sel_rhs
      self.final_stmts.append("{} = {}".format(sel_lhs, sel_rhs))

    if not self.cond_stmts[cond_lhs]:  # empty
      cond_rhs = self.stmts[cond_lhs]
      self.final_stmts.remove("{} = {}".format(cond_lhs, cond_rhs))

  def isIf(self, l):
    tok_types = [t.type for t in self.tokenize(l)]
    if ('IF' in tok_types) and ('ELSE' not in tok_types):
      return True
    else:
      return False

  def isElseIf(self, l):
    tok_types = [t.type for t in self.tokenize(l)]

    if 'ELSE' in tok_types and 'IF' in tok_types:
      return True
    else:
      return False

  def isElse(self, l):
    tok_types = [t.type for t in self.tokenize(l)]

    if 'ELSE' in tok_types:
      return True
    else:
      return False

  def pre_if(self, l, if_type):
    self.lexer.input(l)

    cond_toks = []
    cond_st = False
    while True:
      tok = self.lexer.token()
      if not tok:
        break
      elif tok.type == 'LPAREN':
        cond_st = True
      elif tok.type == 'RPAREN':
        break
      elif cond_st:
        cond_toks.append(tok.value)

    cond = ' '.join(cond_toks)

    cond_lhs = self.pkt_name + "_" + self.branch_var_prefix + str(self.branch_var_cnt)
    self.branch_var_cnt += 1

    self.cond_stmts[cond_lhs] = {}

    cond = self.process_rhs(cond, "bool")
    self.cond[cond_lhs] = cond

    cond_rhs_toks = []
    # get negation of conditions in stack
    for cond_var, _ in self.cond_stack:
      if self.cond[cond_var] == "":
        continue
      cond_rhs_toks.append("!({})".format(self.cond[cond_var]))

    cond_rhs_toks.append("({})".format(cond))
    cond_rhs = " && ".join(cond_rhs_toks)

    self.stmts[cond_lhs] = cond_rhs
    self.final_stmts.append("{} = {}".format(cond_lhs, cond_rhs))
    self.cond_stack.append((cond_lhs, if_type))

  def pre_else(self):
    cond_lhs = self.pkt_name + "_" + self.branch_var_prefix + str(self.branch_var_cnt)
    self.branch_var_cnt += 1

    self.cond[cond_lhs] = ""
    self.cond_stmts[cond_lhs] = {}

    cond_rhs_toks = []

    for cond_var, _ in self.cond_stack:
      if self.cond[cond_var] == "":
        continue
      cond_rhs_toks.append("!({})".format(self.cond[cond_var]))
    # cond_rhs_toks.append("!{}".format(cond_var))

    cond_rhs = " && ".join(cond_rhs_toks)

    self.stmts[cond_lhs] = cond_rhs
    self.final_stmts.append("{} = {}".format(cond_lhs, cond_rhs))
    self.cond_stack.append((cond_lhs, "ELSE"))

  def post_cond(self):
    # pop till (and including) most recent IF
    cond_var, cond_type = self.cond_stack[-1]
    while len(self.cond_stack) > 0 and (cond_type != "IF"):
      self.cond_stack.pop()
      cond_var, cond_type = self.cond_stack[-1]

    # cond_type is IF
    assert (len(self.cond_stack) > 0)
    assert (cond_type == "IF")
    self.cond_stack.pop()

  def in_if(self):
    if len(self.cond_stack) == 0:
      return False
    return self.cond_stack[-1][1] == "IF"

  def in_else_if(self):
    if len(self.cond_stack) == 0:
      return False
    return self.cond_stack[-1][1] == "ELSE_IF"

  def in_else(self):
    if len(self.cond_stack) == 0:
      return False
    return self.cond_stack[-1][1] == "ELSE"

  def process_function(self):
    # print(self.declarations)
    # print(self.state_variables)
    print(self.var_type)
    i = 0
    while i < len(self.func_lines):
      l = self.func_lines[i]
      print("line", l)

      if l.isspace():
        pass

      elif self.isIf(l):
        self.pre_if(l, "IF")

      elif (self.in_if() or self.in_else_if()) and ("}" in l):
        cond_lhs, _ = self.cond_stack[-1]
        self.selector_stmts(cond_lhs)

        print("in_if, {")
        if self.isElseIf(l):
          self.pre_if(l, "ELSE_IF")

        elif self.isElse(l):
          self.pre_else()

        else:
          j = i + 1
          while j < len(self.func_lines) and self.func_lines[j].isspace():
            j += 1

          if j < len(self.func_lines) and (self.isElseIf(self.func_lines[j])):
            self.pre_if(self.func_lines[j], "ELSE_IF")
            i = j

          elif j < len(self.func_lines) and (self.isElse(self.func_lines[j])):
            self.pre_else()
            i = j
          else:
            # no else: pop stack till (including) most recent if
            self.post_cond()
            i = j - 1


      elif self.in_else() and ("}" in l):
        cond_lhs, _ = self.cond_stack[-1]
        self.selector_stmts(cond_lhs)
        self.post_cond()

      elif len(self.cond_stack) > 0:  # inside if or else
        print("inside if else")
        assgn_idx = l.find('=')
        assert (assgn_idx != -1)
        lhs = l[:assgn_idx]
        lhs = lhs.strip()
        lhs = self.process_lhs(lhs, no_idx=True)

        cond_lhs, branch = self.cond_stack[-1]

        if lhs not in self.cond_stmts[cond_lhs]:
          self.cond_stmts[cond_lhs][lhs] = {}

          if lhs not in self.var_idx:
            self.var_idx[lhs] = 0

          self.cond_stmts[cond_lhs][lhs]["O"] = self.var_idx[lhs]  # idx of lhs before cond

        self.process_assgn(l)
        self.cond_stmts[cond_lhs][lhs]["T"] = self.var_idx[lhs]  # SSA index

      else:  # assignment
        self.process_assgn(l)

      i += 1

    # write flanks:
    print("write flanks")
    for pkt_var, state_var in self.pkt_state_map.items():
      idx = self.var_idx[pkt_var]
      if idx > 0:  # if idx = 0, state var has only been read, not written
        pkt_v = pkt_var + str(idx)
        print(pkt_v, self.stmts[pkt_v])
        # optimization: eliminate extra pkt field
        if len(self.stmts[pkt_v].split()) == 1:
          self.final_stmts.remove("{} = {}".format(pkt_v, self.stmts[pkt_v]))
          pkt_v = self.stmts[pkt_v]

        self.final_stmts.append("{} = {}".format(state_var, pkt_v))

    print(self.final_stmts)

  def process_input(self):
    packet_struct = False
    state_def = False
    func_st = False
    packet_var_type = []
    l = f.readline()

    while l:
      # print(l)
      # print("packet_struct", packet_struct, "state_def", state_def, "func_st", func_st)
      if l.isspace():
        pass
      elif l.startswith("//"):  # comment
        pass
      elif l.startswith("#define"):  # macro
        toks = l.split()
        macro_name = toks[1]
        macro_name = macro_name.strip()
        macro_value = toks[2]
        self.macros[macro_name] = macro_value
      elif l.startswith("struct Packet"):
        packet_struct = True
      elif packet_struct:
        if l.startswith("}"):
          packet_struct = False
          state_def = True
        else:
          toks = l.split()
          var_type = toks[0]
          var_name = toks[1]
          var_name = var_name.strip()
          var_name = var_name.replace(';', '')
          packet_var_type.append((var_name, var_type))

      elif l.startswith("void "):
        print("found void func")
        toks = self.tokenize(l)
        if toks[-1].value == "{":
          self.pkt_name = toks[-3].value  # pkt_name, ), {
        else:
          self.pkt_name = toks[-2].value  # pkt_name, )

        print("pkt_name", self.pkt_name)
        state_def = False
        func_st = True

        for var_name, var_type in packet_var_type:
          var_name = self.pkt_name + "." + var_name
          self.packet_variables.append(var_name)
          self.var_idx[var_name] = 0
          self.var_type[var_name] = var_type


      elif state_def:
        toks = l.split()
        var_type = toks[0].strip()
        var_name = toks[1].strip()
        var_name = var_name.replace(";", "")

        pos = var_name.find('[')
        if pos != -1:  # extract array name, if array definition
          var_name = var_name[:pos]

        # self.var_name[var_name] = var_name_new
        self.var_type[var_name] = var_type
        self.var_idx[var_name] = 0
        self.state_variables.append(var_name)

      elif func_st:
        self.func_lines.append(l)

      l = f.readline()

    self.func_lines = self.func_lines[:-1]  # remove last line ("}\n")
    self.process_function()

    print("final stmts")
    self.process_array_stmts()
    for i in self.final_stmts:
      print(i)

    self.write_output()

  def write_output(self):
    f_out = open(self.outfilename, "w")

    for var, ty in self.var_type.items():
      if var not in self.state_variables:
        for i in range(self.var_idx[var] + 1):
          stmt = "{} {}{};\n".format(ty, var, i)
          stmt = stmt.replace(".", "_")
          f_out.write(stmt)

    f_out.write("# state variables start\n")
    for var in self.state_variables:
      ty = self.var_type[var]
      stmt = "{} {};\n".format(ty, var)
      stmt = stmt.replace(".", "_")
      f_out.write(stmt)
    f_out.write("# state variables end\n")

    for var, _ in self.cond.items():
      stmt = "bit {};\n".format(var)
      stmt = stmt.replace(".", "_")
      f_out.write(stmt)

    f_out.write("# declarations end\n")

    for i in self.final_stmts:
      i = i.replace(".", "_")
      f_out.write(i + ";\n")

    f_out.close()

  def process_array_stmts(self):
    import re 
    processed = []
    for stmt in self.final_stmts:
      processed.append(re.sub(r'\[.*\]', '', stmt))
    self.final_stmts = processed

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: <input file name> <output file name>")
    exit(1)

  filename = sys.argv[1]
  outputfilename = sys.argv[2]

  f = open(filename, "r")
  pp = Preprocessor(f, outputfilename)

  # f_out = open(outputfilename, "w+")

  f.close()
