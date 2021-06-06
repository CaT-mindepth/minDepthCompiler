import sys
import ply.lex as lex
import ply.yacc as yacc
import lexerRules


# from lexerRules import tokens

class SketchOutputParser:  # parses a line of Sketch's output
  precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'LT', 'GEQ', 'EQ', 'NEQ'),
    ('right', 'UMINUS'),
  )

  cnt = 0  # counter used to generate intermediate variabless

  stmt_map = {}  # key: lhs, value: rhs Q) Also mark it to be deleted if necessary?
  three_addr_code = []  # list of three-address code statements
  to_be_deleted_stmts = set()  # statements to be deleted

  def __init__(self, lhs_val):
    self.tokens = lexerRules.tokens
    self.lexer = lex.lex(module=lexerRules)
    self.parser = yacc.yacc(module=self)

    self.lhs = lhs_val

  def p_program(self, p):
    '''
    program : assign
        | expr
        | assertexpr
    '''
    p[0] = p[1]

  def p_assertexpr(self, p):
    '''
    assertexpr : ASSERT LPAREN expr EQ expr RPAREN
    '''
    # print("assertexpr")

    expr_lhs = p[3]
    expr_rhs = ""
    if expr_lhs in self.stmt_map:
      expr_rhs = self.stmt_map[expr_lhs]
      self.to_be_deleted_stmts.add(
        "%s = %s" % (expr_lhs, expr_rhs))  # delete this and use the given lhs instead of the tmp_var

    stmt = "%s = %s" % (self.lhs, expr_rhs)
    self.stmt_map[self.lhs] = expr_rhs
    self.three_addr_code.append(stmt)

    if p[5] in self.stmt_map:
      self.to_be_deleted_stmts.add(
        "%s = %s" % (p[5], self.stmt_map[p[5]]))  # delete, since this is the input expression

  def p_assign(self, p):
    '''assign : ID ASSIGN expr
    '''
    p[0] = p[1]  # propagate id
    # print("assign")

    lhs = p[1]
    expr_lhs = p[3]
    expr_rhs = ""
    if expr_lhs in self.stmt_map:
      expr_rhs = self.stmt_map[expr_lhs]

    stmt = "%s = %s" % (lhs, expr_rhs)
    self.stmt_map[lhs] = expr_rhs
    self.three_addr_code.append(stmt)

    if self.is_tmp_var(expr_lhs):  # temp variable
      assert (expr_lhs in self.stmt_map)
      self.to_be_deleted_stmts.add("%s = %s" % (expr_lhs, self.stmt_map[expr_lhs]))

  def p_expr(self, p):
    '''
    expr : expr PLUS term
       | expr MINUS term
       | expr MULT term
       | expr LT expr
       | expr GT expr
       | expr LEQ expr
       | expr GEQ expr
       | expr NEQ expr
       | expr EQ expr
       | expr AND expr
       | expr OR expr
       | term
    '''
    if len(p) == 2:  # term
      p[0] = p[1]
    else:
      tmp_var = self.get_intermediate_assgn(p)
      p[0] = tmp_var

  # def p_expr_neg(self, p):
  # 	'''
  # 	expr : NEG expr
  # 	'''
  # 	tmp_var = self.get_intermediate_assgn(p)
  # 	p[0] = tmp_var

  def p_expr_uminus(self, p):
    'expr : MINUS expr %prec UMINUS'

    print("uminus")
    expr_lhs = p[2]
    tmp_var = self.get_intermediate_assgn(p)
    p[0] = tmp_var

  def p_term_num_id(self, p):
    '''
    term : NUMBER
       | ID
       | NOT term
       | LPAREN expr RPAREN
    '''
    if len(p) == 2:  # ID, NUMBER
      p[0] = str(p[1])
    elif len(p) == 3:  # NEG
      print("found neg")
      tmp_var = self.get_intermediate_assgn(p)
      p[0] = tmp_var
    else:
      p[0] = p[2]

  # Error rule for syntax errors
  def p_error(self, p):
    print("Syntax error!", p)

  def run_parser_basic(self, input_str):
    parser = yacc.yacc()
    result = parser.parse(input_str)
    print(result)

  def get_tmp_var(self):
    var = "tmp_" + str(self.cnt)
    self.cnt += 1
    return var

  def is_tmp_var(self, var):
    if "var".startswith("tmp_"):
      return True
    else:
      return False

  def get_intermediate_assgn(self, p):  # returns the new intermediate variable
    lhs = self.get_tmp_var()
    rhs = " ".join(p[1:])
    rhs = rhs.replace("! ", "!")
    stmt = "%s = %s" % (lhs, rhs)
    # print(stmt)
    self.stmt_map[lhs] = rhs
    self.three_addr_code.append(stmt)
    return lhs

  def run_parser(self, inputfile, to_be_deleted_stmts_init):

    f = open(inputfile, "r")

    l = f.readline()
    while not l.startswith("void sketch "):
      l = f.readline()

    l = f.readline()  # {
    l = f.readline()
    while not l.startswith("}"):
      l = l.replace("&", "&&")  # safe assuming no reference variables
      l = l.replace("|", "||")
      l = l.lstrip()

      if l.isspace():
        pass
      elif l.startswith("assert"):
        self.parser.parse(l)
      else:
        print("appending line ", l)
        self.three_addr_code.append(
          l.rstrip().replace(";", ""))  # assignment statements before assert will be in three-addr code (TODO: check)

      l = f.readline()

    stmts = []
    print("Sketch output stmts")
    print(self.to_be_deleted_stmts)
    for s in self.three_addr_code:
      if (s not in self.to_be_deleted_stmts) and (s not in to_be_deleted_stmts_init):
        print(s)
        stmts.append(s)

    return stmts


if __name__ == "__main__":

  if len(sys.argv) < 4:
    print("Usage: python3 parser.py inputfile lhs outputfile")
    exit(1)

  inputfile = sys.argv[1]
  lhs = sys.argv[2]
  outputfile = sys.argv[3]

  # f_lhs = open(lhsfile, "r")
  # lhs_val = f_lhs.readline().rstrip()
  lhs_val = lhs.rstrip()

  f_out = open(outputfile, "w+")

  outputParser = SketchOutputParser(lhs_val)
  outputParser.run_parser(inputfile, [])
