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
        print(' --------- processing stateless output --------- ')

        lineno = 0

        def parse_sketch(fd, lineno):
            done = False
            while not done:
                l = fd.readline().strip()
                lineno += 1
                if l.startswith('alu'):
                    alu = DominoALU(self.alu_id, l, lineno)
                    self.add_new_alu(alu, input_file)
                elif l.startswith('}'):
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
