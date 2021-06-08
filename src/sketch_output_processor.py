from os import confstr
import sys
import lexerRules
import ply.lex as lex
import networkx as nx


class GenericALU(object):
    #
    # ruijief: we maintain a dict of additional attributes
    # that can be set for each ALU object. This comes in handy
    # when we're doing the final P4 program code generation.
    #
    def __init__(self):
        self.attributes = {}  # This needs to be overridden

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def get_attribute(self, key):
        return self.attributes[key]

    @staticmethod
    def get_default_SALU():
        salu = GenericALU()
        salu.set_type("STATEFUL")
        salu.set_id(-1)
        return salu

    @staticmethod
    def get_default_ALU():
        alu = GenericALU()
        alu.set_type("STATELESS")
        alu.set_id(-1)
        return alu

    def get_type(self):
        return self.alu_type

    def get_id(self):
        return self.id

    # can be "STATEFUL" or "STATELESS"
    def set_type(self, alu_type):
        if alu_type != "STATEFUL" and alu_type != "STATELESS":
            raise Exception("err: invalid alu type: " + alu_type)
        self.alu_type = alu_type

    # id is an integral type
    def set_id(self, id):
        self.id = id


class SALU(GenericALU):
    # ruijief:
    # this represents a Stateful ALU object.
    """ Payloads:
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

    def __init__(self, id, alu_filename, metadata_lo_name, metadata_hi_name,
                 register_lo_0_name, register_hi_1_name, out_name):
        super().__init__()
        self.alu_type = "STATEFUL"
        self.id = id
        self.alu_filename = alu_filename
        self.salu_arguments = ['metadata_lo', 'metadata_hi',
                               'register_lo_0', 'register_hi_1', '_out']
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
        # dict for storing expressions of synthesized variables.
        self.var_expressions = {}
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
            if var_name == '_out[1]':
                return True, 'output_value'
        return False, None

    def process_salu_function(self):
        with open(self.alu_filename) as f:
            l = f.readline()
            # navigate to the line 'void salu'
            while not l.startswith('void salu'):
                l = f.readline()
            l = f.readline()  # eat the '{' symbol
            l = f.readline()  # first line in function block
            lexer = lex.lex(module=lexerRules)
            # this right bracket denotes the termination of the salu function. We recursively visit each stmt block inside this.
            while not l.startswith('}'):
                lexer.input(l)
                toks = []
                for tok in lexer:
                    toks.append(tok)
                if toks[0].type == 'ID':
                    is_lhs_good, demangled = self.demangle(toks[0].value)
                    if is_lhs_good:  # found a var whose expression we need to keep track of.
                        assert(toks[1].type == 'ASSIGN')  # lhs '=' rhs
                        self.var_expressions[demangled] = toks[2:]
                elif toks[0].type == 'RBRACKET':
                    break
                # read the next line.
                l = f.readline()


class ALU(GenericALU):
    # ruijief:
    # an ALU object represents a physical ALU. We will use this class
    # to represent a node in the dependency graph we feed to ILP,
    # and different ALUs will have different edges (which model ILP dependencies).
    # ALU(id, stmt, lineno, wire)
    #  id: the ID of the ALU, usually numbered [1...N] where N is the number of ALUs.
    #  stmt: The statement of the
    def __init__(self, id, stmt, lineno, wire=False):
        super().__init__()
        self.alu_type = "STATELESS"
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
            # last argument is the output variable
            self.output = arg_tokens[-1].value

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
            print("{} = ALU(opcode={}, inputs={})".format(
                self.output, self.opcode, ", ".join(self.inputs), ))
        else:
            print("{} = {}".format(self.output, self.inputs[0]))


class SketchOutputProcessor(object):
    # comp_graph is the component graph from synthesis.py
    def __init__(self, comp_graph):
        self.dependencies = {}  # key: alu, value: list of alus depending on key
        self.rev_dependencies = {}  # key: alu, value: list of alus that key depends on
        self.alus = []
        self.alu_id = 0
        self.comp_graph = comp_graph
        self.salus = []
        self.alu_compnames = {}

    # map a file name to its corresponding component name in the components graph.

    def filename_to_compname(self, filename):
        import re
        a = re.findall(filename, 'comp_[0-9]*')[0]
        if len(a) > 0:
            return a[0]
        else:
            return None

    # add a new ALU (stateful or stateless) to the ALU graph
    def add_new_alu(self, alu):
        self.alu_compnames[self.alu_id] = self.filename_to_compname(input_file)
        if self.alu_compnames[self.alu_id] == None:
            raise Exception("invalid filename: " + input_file)
        self.alu_id += 1
        self.alus.append(alu)
        self.dependencies[alu] = []
        self.rev_dependencies[alu] = []
        self.alu_id += 1

    def process_stateless_output(self, input_file, output):
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

            # alu stmt
            elif l_toks[0].type == 'ID' and l_toks[0].value.startswith("alu"):
                alu = ALU(self.alu_id, l, lineno)
                self.add_new_alu(alu)

            l = f.readline()
            lineno += 1

        if len(self.alus) > 0:  # not just an assignment
            # rename last ALU's output
            self.alus[-1].output = output

    # process outputs from a list of sketch files, each containing
    # one stateful ALU.

    def process_stateful_outputs(self, input_files, output):
        for input_file in input_files:
            self.process_single_output(input_file, output)

    # process a stateful ALU from a single stateful sketch file.
    def process_single_stateful_output(self, input_file, output):
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

            # alu stmt
            elif l_toks[0].type == 'ID' and l_toks[0].value.startswith("salu"):
                # (self, id, alu_filename, metadata_lo_name, metadata_hi_name,
                #        register_lo_0_name, register_hi_1_name, out_name):
                alu = SALU(self.alu_id, input_file, l_toks[2].value,
                           l_toks[3].value, l_toks[4].value, l_toks[5].value, lhs_assert)
                self.add_new_alu(alu)

            l = f.readline()

    # ruijief:
    # find_dependencies finds dependencies (i.e. directed edges) between ALUs, which are nodes
    # in the ILP dependency graph.

    def find_stateless_dependencies_comp(self):
        for alu1 in self.alus:
            if alu1.get_type() == "STATELESS":
                for alu2 in self.alus:
                    if alu2.get_type() == "STATELESS":
                        if alu2 != alu1 and alu1.output in alu2.inputs and alu1.lineno < alu2.lineno:  # RAW
                            self.dependencies[alu1].append(alu2)
                            self.rev_dependencies[alu2].append(alu1)

    def all_stateful_alus(self):
        return filter(lambda x: x.get_type() == "STATEFUL", self.alus)

    def all_stateless_alus(self):
        return filter(lambda x: x.get_type() == "STATELESS", self.alus)

    def alus_in_a_component(self, comp_name):
        return filter(lambda x: self.alu_compnames[x] == comp_name, self.alus)

    # Lower dependencies between stateful components in the component graph
    # into the ALU dependency graph. Here we find only dependencies between
    # stateful ALUs (resp. components).

    def find_stateful_dependencies(self):
        for alu in self.all_stateful_alus():
            alu_compname = self.alu_compnames[alu]
            for comp in self.comp_graph:
                if comp.name == alu_compname:
                    for comp1 in self.comp_graph.predecessor(comp):
                        if comp1.isStateful:
                            # No need to check if alu1 is stateful, since by
                            # definition a stateful component (comp1) only includes a single stateful ALU.
                            for alu1 in self.alus_in_a_component(comp1):
                                self.dependencies[alu].append(alu1)
                                self.rev_dependencies[alu1].append(alu)

    # Lower dependencies from/to a stateless weakly connected component.
    # This includes exactly the edges from/to a stateful component.
    # edges added will be of the form (u,v) where exactly one of {u,v} is
    # stateful and exactly one of {u,v} is stateless.
    def find_stateless_dependencies_intercomp(self):
        for alu in self.all_stateless_alus():
            comp_name = self.alu_compnames[alu]
            # XXX: Here we have to iterate through the component graph,
            # since each node is a component type but not a string.
            # We might want to find a faster way to directly query for the
            # component with name == comp_name in O(1) time.
            for comp in self.comp_graph:
                if comp.name == comp_name:
                    # Find all stateful components going into the current
                    # stateless weakly connected component.
                    for comp1 in self.comp_graph.predecessor(comp):
                        # By definition comp1 is stateful.
                        assert comp1.isStateful
                        # For each ALU in the stateful component, add dependency
                        # from that ALU into us.
                        for alu1 in self.alus_in_a_component(comp1):
                            self.dependencies[alu].append(alu1)
                            self.rev_dependencies[alu1].append(alu)
                    # Find all stateful components that follows from the
                    # current weakly connected component.
                    for comp1 in self.comp_graph.successor(comp):
                        # Again, by definition comp1 is stateful.
                        assert comp1.isStateful
                        # For each ALU in the stateful component, add dependency
                        # from that ALU into us.
                        for alu1 in self.alus_in_a_component(comp1):
                            self.dependencies[alu1].append(alu)
                            self.rev_dependencies[alu].append(alu1)

    # returns a table name object
    def to_ILP_TableInfo(self, table_name):
        import ILP_Gurobi
        num_alus = len(self.alus)
        alu_adjacency_list = [[] for i in range(num_alus)]
        for alu in self.alus:
            for nbor in self.dependencies[alu]:
                alu_adjacency_list[alu.id].append(nbor)
        return ILP_Gurobi.ILP_TableInfo(table_name, num_alus, self.alus, alu_adjacency_list)

    # return part of ILP solver configuration,
    # more specifically the part that specifies the
    # ALU dependencies inside a table in Action Info.

    def to_ILP_str(self, table_name):
        act_info = table_name + ":" + str(len(self.alus))
        for alu in self.alus:
            for nbor in self.dependencies[alu]:
                act_info += ";" + "(" + str(alu.id) + "," + str(nbor.id) + ")"
        return act_info


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
