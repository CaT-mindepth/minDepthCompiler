import sys
import argparse
import ply.lex as lex
import ply.yacc as yacc
import lexerRules
import parser
import time
import subprocess
# import sympy
import dependencyGraph as depG
import synthesis
import scheduler
import re


def has_rel_op(s):
  rel_ops = [">", "<", "==", "!=", "<=", ">="]
  for op in rel_ops:
    if op in s:
      return True

  return False


def has_only_inequality(s):
  rel_ops = [">", "<", "==", "!=", "<=", ">="]
  for op in rel_ops:
    if op == "!=":
      if op not in s:
        return False
    else:
      if op in s:
        return False
  return True


def has_bool_op(s):
  bool_ops = ["&&", "||", "!"]
  for op in bool_ops:
    if op in s:
      return True

  return False


def is_bool_op(s):
  bool_ops = ["&&", "||", "!"]
  if s in bool_ops:
    return True
  else:
    return False


def useful_extra_stmt(stmt, rhs_toks):  # necessary?
  if (len(rhs_toks) == 1) and (rhs_toks[0].type == 'ID'):  # stmt of the form a = b;
    return False
  else:  # TODO: more cases?
    return True


# def simplify_rel(expr):
# 	# remove enclosing parentheses
# 	if expr[0] == "(":
# 		expr = expr[1:]
# 	if expr[-1] == ")":
# 		expr = expr[:-1]
		
# 	print("simplifying relational expression: " + expr)
# 	rel_ops = [">", "<", "==", "!=", "<=", ">="]
# 	new_expr = expr
# 	if ("==" not in expr) and ("!=" not in expr):
# 		new_expr = sympy.sstr(sympy.sympify(expr))
# 	elif "==" in expr:
# 		operands = expr.split("==")
# 		assert(len(operands) == 2)
# 		operands = [x.strip() for x in operands]
# 		print("operands", operands)
# 		if operands[0].isdigit() and operands[1].isdigit():
# 			print("numerical expression")
# 			new_expr = sympy.sstr(sympy.sympify(expr))
# 		else:
# 			lhs = sympy.sstr(sympy.sympify(operands[0]))
# 			rhs = sympy.sstr(sympy.sympify(operands[1]))
# 			if lhs == rhs: # handle this case separately
# 				new_expr = "True"
# 			else:
# 				new_expr = "{} == {}".format(lhs, rhs)

# 	elif "!=" in expr:
# 		operands = expr.split("!=")
# 		assert(len(operands) == 2)
# 		operands = [x.strip() for x in operands]
# 		print("operands", operands)
# 		if operands[0].isdigit() and operands[1].isdigit():
# 			print("numerical expression")
# 			new_expr = sympy.sstr(sympy.sympify(expr))
# 		else:
# 			lhs = sympy.sstr(sympy.sympify(operands[0]))
# 			rhs = sympy.sstr(sympy.sympify(operands[1]))
# 			if lhs == rhs:
# 				new_expr = "False"
# 			else:
# 				new_expr = "{} != {}".format(lhs, rhs)
# 	else:
# 		assert(False)
# 	print("to " + new_expr)
# 	return new_expr

# def simplify_bool(expr):
# 	print("simplifying bool expression: " + expr)
# 	tokens = tokenize_expr(expr)[0]
# 	new_tokens = []
# 	for tok in tokens:
# 		new_tok = tok.value
# 		if tok.value == "&&":
# 			new_tok = "&"
# 		elif tok.value == "||":
# 			new_tok = "|"
# 		elif tok.value == "!":
# 			new_tok = "~"
# 		new_tokens.append(new_tok)

# 	assert(len(new_tokens) == len(tokens))
# 	expr = " ".join(new_tokens)
# 	print("Expression with sympy operators:" + expr)

# 	expr = sympy.sstr(sympy.sympify(expr))

# 	expr = expr.replace("&", "&&")
# 	expr = expr.replace("|", "||")
# 	expr = expr.replace("~", "!")

# 	print("to ", expr)

# 	return expr

# def simplify_arith(expr):
# 	print("simplifying arith expression: " + expr)
# 	expr = sympy.sstr(sympy.sympify(expr))
# 	print("to ", expr)
# 	return expr

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

  def __init__(self, filename, outputfilename):
    self.filename = filename
    self.outputfilename = outputfilename
    self.tmp_cnt = 0

    self.get_type_info()

  def write_expr_generator(self, f):
    f.write(
      "generator int expr(fun vars, int bnd) {\n \
      assert bnd >= 0;\n \
      int t = ??(2);\n \
      if (t == 0) {\n \
        return vars();\n \
      }\n \
      if (t == 1) {\n \
        return ??;\n \
      }\n \
      if (t == 2) {\n \
        return -??;\n \
      }\n \
      else {\n \
        return {| expr(vars, bnd-1) ( + | - ) expr(vars, bnd-1) |};\n \
      }\n \
    }\n"
    )

    f.write(
      "generator int ite_expr(fun vars, int bnd) {\n \
      t = ??(2);\n \
      if (t == 0) {\n \
        return (vars() != 0) ? vars() : vars();\n \
      }\n \
      if (t == 1) {\n \
        return (vars() != 0) ? vars() : ??;\n \
      }\n \
      else {\n \
        return (vars() != 0) ? vars() : -??;\n \
      }\n \
    }\n"
    )

    f.write(
      "generator bit rel_expr(fun vars, int bnd) {\n \
      int t = ??(2);\n \
      assert bnd >= 0;\n \
      if (t == 0) {\n \
        return 0;\n \
      }\n \
      if (t == 1) {\n \
        return 1;\n \
      }\n \
      else {\n \
        return {| expr(vars, bnd-1) (== | != | < | >=) expr(vars, bnd-1)|};\n \
      }\n \
    }\n"
    )
    f.write(
      "generator bit bool_expr(fun vars, int bnd) {\n \
      int t = ??(2);\n \
      assert bnd >= 0;\n \
      if (t == 0) {\n \
        return (vars() != 0);\n \
      }\n \
      if (t == 1) {\n \
        return {| bool_expr(vars, bnd-1) & bool_expr(vars, bnd-1)|};\n \
      }\n \
      else {\n \
        return {| bool_expr(vars, bnd-1) | bool_expr(vars, bnd-1)|};\n \
      }\n \
    }\n"
    )

  def write_harness(self, f, expr, extra_stmts, vars):
    f.write("harness void sketch(")
    if len(vars) >= 1:
      var_type = self.var_types[vars[0]]
      f.write("%s %s" % (var_type, vars[0]))

    for v in vars[1:]:
      var_type = self.var_types[v]
      f.write(", ")
      f.write("%s %s" % (var_type, v))

    f.write(") {\n")

    f.write("\tgenerator int vars(){\n")
    f.write("\t\treturn {|")
    for v in vars:
      if self.var_types[v] == "int":
        f.write(" %s |" % v)
    f.write("};\n")
    f.write("\t}\n")

    if "bit" in self.var_types.values():
      f.write("\tgenerator bit bool_vars(){\n")
      f.write("\t\treturn {|")
      for v in vars:
        if self.var_types[v] == "bit":
          f.write(" %s |" % v)
      f.write("};\n")
      f.write("\t}\n")

    # print("extra stmts")
    for stmt in extra_stmts:
      # print(stmt)
      f.write("\t" + stmt)

    f.write("\tint bnd = ??;\n")
    f.write("\tassert expr(vars, bnd) == " + "(%s);\n" % expr)
    f.write("\tminimize(bnd);\n")
    f.write("}\n")

  def write_harness_bnd(self, f, expr, extra_stmts, vars, bnd, lhs_type):
    f.write("harness void sketch(")
    if len(vars) >= 1:
      var_type = self.var_types[vars[0]]
      f.write("%s %s" % (var_type, vars[0]))

    for v in vars[1:]:
      var_type = self.var_types[v]
      f.write(", ")
      f.write("%s %s" % (var_type, v))

    f.write(") {\n")

    print("var_types values", self.var_types.values())
    if "int" in [self.var_types[v] for v in vars]:
      f.write("\tgenerator int vars(){\n")
      f.write("\t\treturn {|")
      for v in vars:
        if self.var_types[v] == "int":
          f.write(" %s |" % v)
      f.write("};\n")
      f.write("\t}\n")

    if "bit" in [self.var_types[v] for v in vars]:
      f.write("\tgenerator bit bool_vars(){\n")
      f.write("\t\treturn {|")
      for v in vars:
        if self.var_types[v] == "bit":
          f.write(" %s |" % v)
      f.write("};\n")
      f.write("\t}\n")

    # print("extra stmts")
    for stmt in extra_stmts:
      # print(stmt)
      f.write("\t" + stmt)

    if lhs_type == "int":
      f.write("\tassert expr(vars, %s) == " % str(bnd) + "(%s);\n" % expr)
    elif (lhs_type == "bit") and ("&" not in expr) and ("|" not in expr) and has_rel_op(expr):
      f.write("\tassert rel_expr(vars, %s) == " % str(bnd) + "(%s);\n" % expr)
    else:
      assert (lhs_type == "bit")
      # f.write("\tassert bool_expr(bool_vars, %s) == " % str(bnd) + "(%s);\n"%expr)
      f.write(
        "\tassert bool_expr(vars, %s) == " % str(bnd) + "(%s);\n" % expr)  # TODO: What if there are int and bool vars?

    f.write("}\n")

  def run_sketch(self, filename, expr, line_no, extra_stmts, vars, lhs, lhs_type):
    basefilename = filename
    print("run_sketch, filename:", filename)
    dot_pos = filename.rfind(".")
    if dot_pos != -1:
      basefilename = filename[: dot_pos]

    # write expr
    lhsfilename = basefilename + "_lhs_%d" % line_no + ".txt"
    f1 = open(lhsfilename, "w+")
    f1.write(lhs)

    result_file = ""

    bnd = 0
    while True:
      sketch_filename = basefilename + "_%d" % line_no + "_bnd_%d" % bnd + ".sk"
      f = open(sketch_filename, "w+")
      self.write_expr_generator(f)
      self.write_harness_bnd(f, expr, extra_stmts, vars, bnd, lhs_type)
      f.close()
      # run Sketch
      sketch_outfilename = sketch_filename + ".out"
      print("sketch %s > %s" % (sketch_filename, sketch_outfilename))

      f_sk_out = open(sketch_outfilename, "w+")

      print("running sketch, bnd = %d" % bnd)
      print("sketch_filename", sketch_filename)
      ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
      print("return code", ret_code)
      if ret_code == 0:  # successful
        print("solved")
        result_file = sketch_outfilename
        print("output is in %s" % result_file)
        break
      else:
        print("failed")

      f_sk_out.close()
      bnd += 1

    assert (result_file != "")
    return (result_file, lhsfilename)

  def parse_rel_bool_expr(self, expr):
    print("expr", expr)

    bool_operands = re.split(r'&& | \|\|', expr)
    # bool_operands = [(x.replace("!", "")).strip() for x in bool_operands] # TODO: Wrong if it contains !=
    for i in range(0, len(bool_operands)):
      operand = bool_operands[i]
      if operand[0] == "!":
        bool_operands[i] = operand[1:].strip()

    print("bool_operands", bool_operands)
    bool_operand_set = set(bool_operands)

    new_bool_var_map = {}  # key: relational expr, value: new bool var/ True / False
    new_bool_var_map_rev = {}

    print("tmp_var maps", self.tmp_vars, self.tmp_vars_rev)

    for operand in bool_operand_set:
      simp_operand = simplify_rel(operand)
      if simp_operand == "True" or simp_operand == "False":
        new_bool_var_map[operand] = simp_operand
      else:
        tmp = 0
        operand_stripped = operand.replace("(", "")
        operand_stripped = operand_stripped.replace(")", "")
        operand_stripped = operand_stripped.strip()

        if operand in self.tmp_vars_rev:
          tmp = self.tmp_vars_rev[operand]
        elif operand_stripped in self.tmp_vars_rev:
          tmp = self.tmp_vars_rev[operand_stripped]
        elif operand in self.rhs_map:
          tmp = self.rhs_map[operand]
        elif operand_stripped in self.rhs_map:
          tmp = self.rhs_map[operand_stripped]
        else:
          tmp = "tmp_bool_{}".format(self.tmp_cnt)
          self.tmp_cnt += 1
          self.tmp_vars_rev[operand] = tmp
          self.tmp_vars[tmp] = operand
          self.var_types[tmp] = "bit"

        new_bool_var_map[operand] = tmp
        new_bool_var_map_rev[tmp] = operand

    bool_expr = expr

    for rel_expr, bool_var in new_bool_var_map.items():  # problem if some rel_expr are subexpressions of others?
      bool_expr = bool_expr.replace(rel_expr, bool_var)

    return (bool_expr, new_bool_var_map, new_bool_var_map_rev)

  def write_code_to_file(self, stmts, bool_expr, f_out, bool_var_map={}, bool_var_rev_map={}):
    if bool_expr:
      for rel_expr, bool_var in bool_var_map.items():
        if bool_var == "True" or bool_var == "False":
          continue
        rel_expr = simplify_rel(rel_expr)
        three_addr_code = self.get_min_depth_expr(rel_expr, bool_var, 0)
        for stmt in three_addr_code:
          f_out.write(stmt + ";\n")

    for s in stmts:
      f_out.write(s + ";\n")

  def get_min_depth_expr(self, rhs_expr, lhs, line_no):
    rhs_toks, rhs_variables = tokenize_expr(rhs_expr)

    if (len(rhs_toks) <= 3) or (len(rhs_variables) == 0):  # already in three-addr code
      print("already in three-addr code")
      return ["{} = {}".format(lhs, rhs_expr)]

    extra_stmts = []
    extra_vars = set()

    # don't include extra stmts for now

    # for v in rhs_variables:
    # 	if v in self.stmt_map:
    # 		extra_stmt_info = self.stmt_map[v][-1]
    # 		stmt = extra_stmt_info[0]
    # 		r_vars = extra_stmt_info[1]
    # 		l_no = extra_stmt_info[2]
    # 		r_tokens = extra_stmt_info[3]
    # 		# if useful_extra_stmt(stmt, r_tokens):
    # 		extra_stmts.append((l_no, stmt))
    # 		extra_vars.update(r_vars)

    extra_stmts.sort()
    stmts = [x[1] for x in extra_stmts]
    extra_stmts_set = set([(x.replace(";", "")).rstrip() for x in stmts])
    rhs_variables.update(extra_vars)
    variables = list(rhs_variables)
    lhs_type = self.var_types[lhs]
    rhs_expr = rhs_expr.replace("&&", "&")
    rhs_expr = rhs_expr.replace("||", "|")

    sketch_outputfile, lhsfile = self.run_sketch(self.outputfilename, rhs_expr, line_no, stmts, variables, lhs,
                                                 lhs_type)
    outputParser = parser.SketchOutputParser(lhs)
    three_addr_stmts = outputParser.run_parser(sketch_outputfile, extra_stmts_set)
    return three_addr_stmts

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


if __name__ == "__main__":
	
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument("input", help="input file (preprocessed Domino program)")
	arg_parser.add_argument("output", help="output directory")
	arg_parser.add_argument("--stages", help="number of pipeline stages", type=int)
	arg_parser.add_argument("--ALUs", help="number of ALUs per stage", type=int)

	args = arg_parser.parse_args()
	# if len(sys.argv) < 5:
	# 	print("Usage: <input file name> <output file name> <max number of stages> <max number of ALUs per stage>")
	# 	exit(1)

	filename = args.input
	outputfilename = args.output
	max_stages = args.stages
	max_alus = args.ALUs

	start = time.time()

	f = open(filename, "r")
	# f_out = open(outputfilename, "w+")

	codeGen = codeGen(filename, outputfilename)
	# codeGen.process_input(f, f_out)

	f.close()
	# f_out.close()


	dep_graph_obj = depG.DependencyGraph(filename, codeGen.state_variables, codeGen.var_types)
	synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, \
					dep_graph_obj.scc_graph, dep_graph_obj.stateful_nodes, outputfilename)
	# dep_graph_obj.write_optimized_code(outputfilename)

	
	# sch = scheduler.Scheduler(dep_graph_obj.dep_graph, max_stages, max_alus)
	# sch.solve()
	# sch.draw_graph()
	
	end = time.time()
	print("Time taken: {} s".format(end - start))
