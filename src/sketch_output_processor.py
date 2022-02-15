from os import confstr

from overrides import overrides
import lexerRules
import ply.lex as lex
import re

from alus import ALU, SALU, GenericOutputProcessor

class SketchOutputProcessor(GenericOutputProcessor):
    # comp_graph is the component graph from synthesis.py
    def __init__(self, comp_graph):
        self.dependencies = {}  # key: alu, value: list of alus depending on key
        self.rev_dependencies = {}  # key: alu, value: list of alus that key depends on
        self.alus = []
        self.alu_id = 0
        self.comp_graph = comp_graph
        self.salus = []
        self.alu_compnames = {}


    @overrides
    def process_stateless_output(self, input_file, output):
        f = open(input_file, "r")
        print('process_stateless_output: processing file ', input_file)
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
                self.add_new_alu(alu, input_file)

            l = f.readline()
            lineno += 1

        if len(self.alus) > 0:  # not just an assignment
            # rename last ALU's output
            self.alus[-1].output = output


    def find_output_dst(self, input_file):
        sketch_file = input_file[:-4] # sans '.out'
        print(' find_output_dst: reading from sketch file ', sketch_file)
        with open(sketch_file, "r") as f:
            specname = self.filename_to_specname(input_file)
            l = f.readline()
            outs = []
            print('find_output_dst: trying to find `void ' + specname + '`')
            while not l.startswith("int[2] " + specname):
                #print('curr line: ' + l)
                l = f.readline()
            print('done')
            while not l.startswith("}"):
                l = f.readline()
                print('curr line: ' + l)
                if l.lstrip().startswith("_out"):
                    print(' > FOUND OUT LINE : ' + l)
                    lexer = lex.lex(module=lexerRules)
                    lexer.input(l)
                    l_toks = []
                    for tok in lexer:
                        l_toks.append(tok)
                    if l_toks[1].type == 'LBRACKET' and l_toks[3].type == 'RBRACKET':
                        if l_toks[2].value == '1':
                            assert (l_toks[-1].type == 'ID')
                            print("> found out variable: ", l_toks[-1].value)
                            outs.append(l_toks[-1].value)
        #print('done ---- outs[-1] is ', outs[-1])
        return outs[-1] if len(outs) > 0 else '0'

    # process a stateful ALU from a single stateful sketch file.
    @overrides
    def process_single_stateful_output(self, input_file, output):
        with open(input_file, "r") as f:
            specname = self.filename_to_specname(input_file)
            l = f.readline()
            while not l.startswith("void sketch"):
                l = f.readline()
            
            l = f.readline()
            # l is "void sketch..."
            l = f.readline()

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

                # alu stmt
                elif l_toks[0].type == 'ID' and l_toks[0].value.startswith("salu"):
                    # (self, id, alu_filename, metadata_lo_name, metadata_hi_name,
                    #        register_lo_0_name, register_hi_1_name, out_name):
                    output_dst = self.find_output_dst(input_file)
                    print('Constructing new SALU: id=', self.alu_id, ' metadata_lo=', l_toks[2].value, \
                        ' metadata_hi=', l_toks[3].value, ' register_lo=', l_toks[4].value, 
                        ' register_hi=', l_toks[5].value, 
                        ' output_dst=', output_dst)
                    alu = SALU(self.alu_id, input_file, l_toks[2].value, \
                      l_toks[3].value, l_toks[4].value, l_toks[5].value, output_dst)
                    self.add_new_alu(alu, input_file)

                l = f.readline()

