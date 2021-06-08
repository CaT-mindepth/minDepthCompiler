import sys
import argparse
import ply.lex as lex
import ply.yacc as yacc
import lexerRules
import parser
import time
import subprocess
import sympy
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


def simplify_rel(expr):
  # remove enclosing parentheses
  if expr[0] == "(":
    expr = expr[1:]
  if expr[-1] == ")":
    expr = expr[:-1]

  print("simplifying relational expression: " + expr)
  rel_ops = [">", "<", "==", "!=", "<=", ">="]
  new_expr = expr
  if ("==" not in expr) and ("!=" not in expr):
    new_expr = sympy.sstr(sympy.sympify(expr))
  elif "==" in expr:
    operands = expr.split("==")
    assert (len(operands) == 2)
    operands = [x.strip() for x in operands]
    print("operands", operands)
    if operands[0].isdigit() and operands[1].isdigit():
      print("numerical expression")
      new_expr = sympy.sstr(sympy.sympify(expr))
    else:
      lhs = sympy.sstr(sympy.sympify(operands[0]))
      rhs = sympy.sstr(sympy.sympify(operands[1]))
      if lhs == rhs:  # handle this case separately
        new_expr = "True"
      else:
        new_expr = "{} == {}".format(lhs, rhs)

  elif "!=" in expr:
    operands = expr.split("!=")
    assert (len(operands) == 2)
    operands = [x.strip() for x in operands]
    print("operands", operands)
    if operands[0].isdigit() and operands[1].isdigit():
      print("numerical expression")
      new_expr = sympy.sstr(sympy.sympify(expr))
    else:
      lhs = sympy.sstr(sympy.sympify(operands[0]))
      rhs = sympy.sstr(sympy.sympify(operands[1]))
      if lhs == rhs:
        new_expr = "False"
      else:
        new_expr = "{} != {}".format(lhs, rhs)
  else:
    assert (False)
  print("to " + new_expr)
  return new_expr


def simplify_bool(expr):
  print("simplifying bool expression: " + expr)
  tokens = tokenize_expr(expr)[0]
  new_tokens = []
  for tok in tokens:
    new_tok = tok.value
    if tok.value == "&&":
      new_tok = "&"
    elif tok.value == "||":
      new_tok = "|"
    elif tok.value == "!":
      new_tok = "~"
    new_tokens.append(new_tok)

  assert (len(new_tokens) == len(tokens))
  expr = " ".join(new_tokens)
  print("Expression with sympy operators:" + expr)

  expr = sympy.sstr(sympy.sympify(expr))

  expr = expr.replace("&", "&&")
  expr = expr.replace("|", "||")
  expr = expr.replace("~", "!")

  print("to ", expr)

  return expr


def simplify_arith(expr):
  print("simplifying arith expression: " + expr)
  expr = sympy.sstr(sympy.sympify(expr))
  print("to ", expr)
  return expr


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
  arg_parser.add_argument("output", help="output file")
  arg_parser.add_argument("--stages", help="number of pipeline stages", type=int)
  arg_parser.add_argument("--ALUs", help="number of ALUs per stage", type=int)

  args = arg_parser.parse_args()

  filename = args.input
  outputfilename = args.output
  max_stages = args.stages
  max_alus = args.ALUs

  start = time.time()

  f = open(filename, "r")

  codeGen = codeGen(filename, outputfilename)

  f.close()

  dep_graph_obj = depG.DependencyGraph(filename, codeGen.state_variables, codeGen.var_types)
  synth_obj = synthesis.Synthesizer(codeGen.state_variables, codeGen.var_types, \
                                    dep_graph_obj.scc_graph, dep_graph_obj.stateful_nodes, outputfilename)

  end = time.time()
  print("Time taken: {} s".format(end - start))
