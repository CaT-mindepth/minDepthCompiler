
"""
    Note: for this project, ALU = stateless ALU, SALU = stateful ALU.
"""
import ply.lex as lex
import lexerRules
class ALU:
  # ruijief: 
  # a stateless ALU object represents a physical ALU. We will use this class
  # to represent a node in the dependency graph we feed to ILP,
  # and different ALUs will have different edges (which model ILP dependencies).
  # ALU(id, stmt, lineno, wire)
  #  id: the ID of the ALU, usually numbered [1...N] where N is the number of ALUs.
  #  stmt: The assignment statement representing the synthesized ALU unit. For instance, 
  #     this may look like `alu(5, p_now, p_now_plus_free, 1, _out_s10)`
  #  lineno: the (relative) line number of the `stmt` ALU expression, relative to the 
  #     start of the `void sketch` function (which is line number 0).
  #  wire: there is no real ALU operation here. Just a renaming of an input variable
  # to an output variable.
  def __init__(self, id, stmt, lineno, wire=False):
    self.id = id
    self.stmt = stmt
    self.lineno = lineno
    self.wire = wire
    self.process_stmt()

  def process_stmt(self):
    if not self.wire:
      lexer = lex.lex(module=lexerRules)
      lexer.input(self.stmt)

      arg_tokens = []
      args_st = False 

      for tok in lexer:
        # print(' > current token: ' + str(tok.value) + '; of type ' + str(tok.type))
        if tok.type == 'RPAREN':
          args_st = False
        elif args_st:
          arg_tokens.append(tok)

        elif tok.type == 'LPAREN':
          args_st = True

      self.opcode = arg_tokens[0].value  # first argument is ALU opcode
      input_tokens = arg_tokens[1:-1] # up to, but not including, last element (which is the output).
      self.inputs = [t.value for t in input_tokens]
      self.output = arg_tokens[-1].value  # last argument is the output variable
    else:
      lexer = lex.lex(module=lexerRules)
      lexer.input(self.stmt)
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
      print("{} = {} #WIRE".format(self.output, self.inputs[0]))

# test
if __name__ == "__main__":
    print("testing new stateless ALU output processor:")
    test_alu = ALU(0, "alu(5, p_now, p_now_plus_free, 1, _out_s10)", 3)
    test_alu.print()
    print("testing a wire ALU: lhs001 = rhs002")
    test_wire = ALU(1, "lhs001 = rhs002", 5, True)
    test_wire.print()