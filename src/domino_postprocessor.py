from os import confstr
from typing import Generic
from overrides import overrides
import lexerRules
import ply.lex as lex
import re

from alus import *


class DominoOutputProcessor(GenericOutputProcessor):
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
        print(' --------- processing stateless output {} --------- '.format(output))

        lineno = 0

        def parse_sketch(fd, lineno):
            done = False
            # temp Sketch outputs
            comp_output = ''
            final_output = ''
            alus_created = []
            while not done:
                l = fd.readline().strip()
                lineno += 1
                if l.startswith('alu'):
                    alu = DominoALU(self.alu_id, l, lineno)

                    self.add_new_alu(alu, input_file)
                    alus_created.append(alu)
                elif l.startswith('comp'):
                    toks = l.strip().split()
                    comp_output = toks[-1]
                    comp_output = comp_output[:comp_output.find(')')]
                elif l.startswith('assert'):
                    toks = l.strip().split()
                    first_var = toks[1]
                    first_var = first_var.replace('(', '')
                    second_var = toks[3]
                    second_var = second_var.replace(')', '')
                    second_var = second_var.replace(';', '')
                    if second_var == comp_output:
                        final_output = first_var
                    else:
                        final_output = second_var
                elif l.startswith('}'):
                    assert(comp_output != '')
                    assert(final_output != '')
                    replaced = False
                    for alu in alus_created:
                        if alu.output == final_output:
                            alu.set_output(output)
                            replaced = True
                    assert(replaced)
                    return lineno
            return lineno

        with open(input_file) as fd:
            done = False
            while not done:
                l = fd.readline().strip()
                lineno += 1
                if l.startswith('void sketch'):
                    lineno = parse_sketch(fd, lineno)
                    done = True

    # process a stateful ALU from a single stateful sketch file.
    @overrides
    def process_single_stateful_output(self, input_file, comp: synthesis.StatefulComponent):
        print(' --------- processing stateful output ---------')
        domino_alu = DominoGenericSALU(self.alu_id, input_file, comp)
        self.add_new_alu(domino_alu, input_file)
