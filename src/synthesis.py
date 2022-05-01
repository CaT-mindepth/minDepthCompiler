import math
from re import A, L
import os
import ply.lex as lex
import networkx as nx
import copy
from graphviz import Digraph
import subprocess
from sketch_output_processor import SketchOutputProcessor
from dependencyGraph import Codelet
from dependencyGraph import Statement
import test_stats
import grammar_util

# Returns true if SSA variables v1 and v2 represent the same variable
# TODO: update preprocessing code to store SSA info in a struct/class
# instead of relying on string matching

def is_same_var(v1, v2):
    if v1 == v2:
        return True

    i = 0
    prefix = ""
    while i < len(v1) and i < len(v2):
        if v1[i] == v2[i]:
            prefix += v1[i]
            i += 1
        else:
            break

    v1_suffix = ""
    v2_suffix = ""
    if i < len(v1):
        v1_suffix = v1[i:]
    if i < len(v2):
        v2_suffix = v2[i:]
    print('is_same_var: ', v1, ' ? ', v2, " => ",
          v1_suffix.isnumeric() and v2_suffix.isnumeric())
    # v1 and v2 represent the same variable if the suffixes are numbers
    return v1_suffix.isnumeric() and v2_suffix.isnumeric()


def get_variable_name(v1, v2):  # longest common prefix
    assert(v1 != v2)
    assert(is_same_var(v1, v2))

    i = 0
    prefix = ""
    while i < len(v1) and i < len(v2):
        if v1[i] == v2[i]:
            prefix += v1[i]
            i += 1
        else:
            break
    return prefix


def is_branch_var(var):
    # ruijief: updated this to make domino preprocessing input work.
    # var.startswith("p_br_tmp") or var.startswith("pkt_br_tmp")
    return "br" in var


def is_tmp_var(var):
    return "tmp" in var


class Component:  # group of codelets
    def __init__(self, codelet_list, id, grammar_name=None, is_tofino=True):
        self.codelets = codelet_list  # topologically sorted
        self.isStateful = False
        self.grammar_name = grammar_name
        self.is_tofino = is_tofino
        self.get_inputs_outputs()
        self.set_component_stmts()
        self.set_name("comp_" + str(id))
        self.bci_inputs = []
        self.bci_outputs = []
        self.is_duplicated = False

    def mark_as_duplicate(self):
        self.is_duplicated = True

    def add_bci_inputs(self, ins):
        self.bci_inputs += (ins)

    def add_bci_outputs(self, outs):
        self.bci_outputs += (outs)

    def set_name(self, name):
        self.name = name

    def is_branch_var(self):
        for out in self.outputs:
            if is_branch_var(out):
                return True
        return False

    def get_inputs_outputs(self):
        inputs = set()
        outputs = set()
        for codelet in self.codelets:
            ins = codelet.get_inputs()
            outs = codelet.get_outputs()
            inputs.update([i for i in ins if i not in outputs])
            outputs.update(outs)

        self.inputs = list(inputs)
        self.outputs = list(outputs)

    def last_ssa_var(self, var):
        ssa_vars = [o for o in self.outputs if o !=
                    var and is_same_var(o, var)]
        if len(ssa_vars) == 0:
            return True  # var is the only SSA variable
        var_name = get_variable_name(var, ssa_vars[0])
        ssa_indices = [int(v.replace(var_name, '')) for v in ssa_vars]
        max_index = max(ssa_indices)
        var_index = int(var.replace(var_name, ''))

        return var_index >= max_index

    def update_outputs(self, adj_comps):
        '''
        Keep output o if
        1. It is used by an adjacent codelet (whether it is a temporary var or not), OR
        2. It is a packet field (SSA var with largest index in this component)
        '''

        redundant_outputs = []
        for o in self.outputs:
            # not used in adjacent component
            if o not in [i for c in adj_comps for i in c.inputs]:
                if not self.last_ssa_var(o):
                    redundant_outputs.append(o)
                    # print("Redundant output: {}".format(o))

        print("redundant outputs", redundant_outputs)

        for red_o in redundant_outputs:
            self.outputs.remove(red_o)

    def set_component_stmts(self):
        self.comp_stmts = []
        for codelet in self.codelets:
            self.comp_stmts.extend(codelet.get_stmt_list())

    # This merge_component should be removed since two stateless components cannot be merged
    def merge_component(self, comp):
        print("merge component")
        self.codelet.add_stmts(comp.comp_stmts)
        if comp.isStateful:
            raise Exception("Cannot merge a stateful comp, " +
                            "comp.name, " + "with a stateless comp")
        else:
            self.set_component_stmts()
            self.get_inputs_outputs()

    def print(self):
        for s in self.comp_stmts:
            s.print()

    def __str__(self):
        return " ".join([s.get_stmt() for s in self.comp_stmts])

    def write_grammar(self, f):
        try:
            f_grammar = open(grammar_util.resolve_stateless(self.is_tofino))
            # copy gramar
            lines = f_grammar.readlines()
            for l in lines:
                f.write(l)

        except IOError:
            print("Failed to open stateless grammar file {}.".format(
                self.grammar_name))
            exit(1)

    def write_weighted_grammar_new(self, f, synth_bounds):
        try:
            f_grammar = open(grammar_util.resolve_stateless(self.is_tofino))
            # copy gramar
            lines = f_grammar.readlines()
            for l in lines:
                if l.strip().startswith("generator"):
                    break # Copy only the alu definition
                f.write(l)
            bnd_vars = self.get_input_bounds(synth_bounds)
            bnds_list = sorted(list(bnd_vars.keys()))
            max_input_bnd = bnds_list[-1]
            min_input_bnd = bnds_list[0]

            # Write generator functions for every bound in [min_input_bnd, max_input_bnd)
            bnd_to_expr = {} # bnd -> (expr name, args)
            # min_input_bnd
            # f.write('generator int expr{}(fun vars{})'.format(min_input_bnd, min_input_bnd) + '{\n')
            # f.write('\treturn vars{}();\n'.format(min_input_bnd))
            # f.write('}\n')
            # bnd_to_expr[min_input_bnd] = (f'expr{min_input_bnd}', [f'vars{min_input_bnd}'])
            bnd_to_expr[min_input_bnd] = (f'vars{min_input_bnd}', [])

            for b in range(min_input_bnd+1, max_input_bnd):
                args = []
                for b1 in bnds_list:
                    if b1 <= b:
                        args.append(b1)

                params = [f'vars{x}' for x in args]
                bnd_to_expr[b] = (f'expr{b}', params)
                defn_params = ', '.join([f'fun {p}' for p in params])
                f.write('generator int expr{}({})'.format(b, defn_params) + '{\n')

                if b not in bnds_list:
                    f.write('\tint t = ??(1);\n')
                else:
                    f.write('\tint t = ??(2);\n')
                # case 1: use expr with bnd b-1
                prev_expr_name = bnd_to_expr[b-1][0]
                prev_params = ', '.join(bnd_to_expr[b-1][1])
                f.write('\tif (t == 0){\n')
                f.write('\t\treturn {}({});\n'.format(prev_expr_name, prev_params))
                f.write('\t}\n')
            
                # case 2: return vars with bnd b (if applicable)
                if b in bnds_list:
                    f.write('\telse if (t == 1){\n')
                    f.write('\t\treturn vars{}();\n'.format(b))
                    f.write('\t}\n')
                # case 3: use an ALU
                f.write('\telse {\n')
                prev_expr_name = bnd_to_expr[b-1][0]
                prev_params = ', '.join(bnd_to_expr[b-1][1])
                prev_expr = '{}({})'.format(prev_expr_name, prev_params)
                if not self.is_tofino:
                    f.write('\t\treturn alu(??, {}, {}, {}, ??);\n'.format(prev_expr, prev_expr, prev_expr))
                else:
                    f.write('\t\treturn alu(??, {}, {}, ??);\n'.format(prev_expr, prev_expr))


                f.write('\t}\n')
                f.write('}\n\n')	

            # Write final expression generator
            vars = ', '.join(['fun vars{}'.format(i) for i in bnds_list]) + ', fun vars'
            f.write('generator int expr({}, int bnd)'.format(vars) + '{\n')
            for gen_bnd, gen_info in bnd_to_expr.items():
                f.write(f'\tif (bnd == {gen_bnd})' + '{\n')
                gen_name = gen_info[0]
                gen_params = gen_info[1]
                gen_params_str = ', '.join(gen_params)
                f.write('\t\treturn {}({});\n'.format(gen_name, gen_params_str))
                f.write('\t}\n')

            f.write('\tint t = ??(1);\n')
            f.write('\tif (t == 0){\n')
            f.write('\t\treturn vars();\n')
            f.write('\t}\n')
            f.write('\telse {\n')
            prev_args = ', '.join(['vars{}'.format(i) for i in bnds_list]) + ', vars'
            prev_expr = 'expr({}, bnd-1)'.format(prev_args)
            if not self.is_tofino:
                f.write('\t\treturn alu(??, {}, {}, {}, ??);\n'.format(prev_expr, prev_expr, prev_expr))
            else:
                f.write('\t\treturn alu(??, {}, {}, ??);\n'.format(prev_expr, prev_expr))

            f.write('\t}\n')
            f.write('}\n')

        except IOError:
            print("Failed to open stateless grammar file {}.".format(self.grammar_name))
            exit(1)

    def write_sketch_spec(self, f, var_types, comp_name, o):
        input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
        spec_name = comp_name

        # write function signature
        f.write("int {}({})".format(spec_name, ", ".join(input_types)) + "{\n")
        # declare defined variables
        defines_set = set()
        for codelet in self.codelets:
            defines_set.update(codelet.get_outputs())

        defines = list(defines_set)

        for v in defines:
            if v not in self.inputs:
                f.write("\t{} {};\n".format(var_types[v], v))
        # function body
        for stmt in self.comp_stmts:
            f.write("\t{}\n".format(stmt.get_stmt()))
        # return
        f.write("\treturn {};\n".format(o))
        f.write("}\n")

    def write_sketch_harness(self, f, var_types, comp_name, o, bnd):
        f.write("harness void sketch(")
        if len(self.inputs) >= 1:
            var_type = var_types[self.inputs[0]]
            f.write("{} {}".format(var_type, self.inputs[0]))

        for v in self.inputs[1:]:
            var_type = var_types[v]
            f.write(", ")
            f.write("{} {}".format(var_type, v))

        f.write(") {\n")

        f.write("\tgenerator int vars(){\n")
        f.write("\t\treturn {| 1 |")
        if "int" in [var_types[v] for v in self.inputs]:
            # f.write("|");
            for v in self.inputs:
                f.write(" {} |".format(v))
        f.write("};\n")
        f.write("\t}\n")

        # no inputs of type bit
        # if self.is_tofino and not ("bit" not in [var_types[v] for v in self.inputs]):
        #    print('ERROR: bit present in inputs')
        #    assert False

        comp_fxn = comp_name + "(" + ", ".join(self.inputs) + ")"

        output_type = var_types[o]
        if self.is_tofino and (not (output_type == "int")):
            raise Exception('Error: Output ' + o +
                            ' is a bit type, not an int')

        f.write("\tassert expr(vars, {}) == {};\n".format(bnd, comp_fxn))

        f.write("}\n")

    def write_sketch_harness_weighted_new(self, f, var_types, comp_name, o, bnd, synth_bounds):
        f.write("harness void sketch(")
        if len(self.inputs) >= 1:
            var_type = var_types[self.inputs[0]]
            f.write("{} {}".format(var_type, self.inputs[0]))

        for v in self.inputs[1:]:
            var_type = var_types[v]
            f.write(", ")
            f.write("{} {}".format(var_type, v))

        f.write(") {\n")

        bnd_vars = self.get_input_bounds(synth_bounds)
        bnds_list = sorted(list(bnd_vars.keys()))
        max_input_bnd = bnds_list[-1]
        for b in bnds_list:
            f.write('\tgenerator int vars{}()'.format(b) + '{\n')
            if b == 0:
                f.write('\t\treturn {| 1 | ' + ' | '.join(bnd_vars[b]) + ' |};\n')
            else:
                f.write('\t\treturn {|' + ' | '.join(bnd_vars[b]) + '|};\n')
            f.write("\t}\n")
        
        f.write('\tgenerator int vars(){\n')
        f.write('\t\treturn {| 1 | ' + ' | '.join(self.inputs) + '|};\n')
        f.write("\t}\n")

        # f.write("\tgenerator int vars(){\n")
        # f.write("\t\treturn {| 1 |".)
        # if "int" in [var_types[v] for v in self.inputs]:
        # 	# f.write("|");
        # 	for v in self.inputs:
        # 		f.write(" {} |".format(v))
        # f.write("};\n")
        # f.write("\t}\n")

        # no inputs of type bit
        if self.is_tofino and not ("bit" not in [var_types[v] for v in self.inputs]):
            print('ERROR: bit present in inputs')
            assert False

        comp_fxn = comp_name + "(" + ", ".join(self.inputs) + ")"

        output_type = var_types[o]
        if self.is_tofino and (not (output_type == "int")):
            raise Exception('Error: Output ' + o + ' is a bit type, not an int')

        f.write("\tassert expr({}, {}) == {};\n".format(
            ', '.join(['vars{}'.format(b) for b in bnds_list] + ['vars']), bnd, comp_fxn))

        f.write("}\n")
        
    def write_sketch_spec_ternary(self, f, var_types, comp_name):
        input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
        spec_name = comp_name
        # write function signature
        f.write("int[3] {}({})".format(
            spec_name, ", ".join(input_types)) + "{\n")
        # declare output array
        output_array = "_out"
        f.write("\tint[3] {};\n".format(output_array))
        # declare defined variables
        defines = []
        for codelet in self.codelets:
            defines += codelet.get_defines()
        for v in defines:
            if v not in self.inputs:
                f.write("\t{} {};\n".format(var_types[v], v))
        # function body
        for stmt in self.comp_stmts:
            f.write("\t{}\n".format(stmt.get_stmt()))
        # update output array
        if not(len(self.outputs) <= 2):
            print('ERROR: outputs are ', self.outputs, ' which is more than 2.')
            print('node: ', str(self))
            assert False
        f.write("\t{}[0] = {};\n".format(output_array, self.outputs[0]))
        if len(self.outputs) > 1:
            f.write("\t{}[1] = {};\n".format(output_array, self.outputs[1]))
            f.write("\t{}[2] = {};\n".format(output_array, self.outputs[0]))
        else:
            f.write("\t{}[1] = 0;\n".format(output_array))
            f.write("\t{}[2] = {};\n".format(output_array, self.outputs[0]))
        # return
        f.write("\treturn {};\n".format(output_array))
        f.write("}\n")

    def write_grammar_ternary(self, f):
        grammar_path = "grammars/stateful_tofino.sk"
        try:
            f_grammar = open(grammar_path)
            # copy gramar
            lines = f_grammar.readlines()
            for l in lines:
                f.write(l)

        except IOError:
            print("Failed to open stateful grammar file {}.".format(grammar_path))
            exit(1)

    def write_sketch_harness_ternary(self, f, var_types, comp_name):
        f.write("harness void sketch(")
        if len(self.inputs) >= 1:
            var_type = var_types[self.inputs[0]]
            f.write("{} {}".format(var_type, self.inputs[0]))

        for v in self.inputs[1:]:
            var_type = var_types[v]
            f.write(", ")
            f.write("{} {}".format(var_type, v))
        f.write(') {\n')
        assert len(self.inputs) <= 2
        if len(self.inputs) == 1:
            f.write('\tint[3] impl = salu({}, 0, 0, 0);\n'.format(self.inputs[0]))
            f.write('\tint[3] spec = {}({});\n'.format(comp_name, self.inputs[0]))
        else:
            f.write('\tint[3] impl = salu({}, {}, 0, 0);\n'.format(self.inputs[0], self.inputs[1]))
            f.write('\tint[3] spec = {}({}, {});\n'.format(comp_name, self.inputs[0], self.inputs[1]))

        f.write("\tassert(impl[0] == spec[0]);\n")
        f.write("\tassert(impl[1] == spec[1]);\n")
        f.write("\tassert(impl[2] == spec[2]);\n")
        f.write("}\n")

    def write_ternary_sketch_file(self, output_path, comp_name, var_types, stats: test_stats.Statistics = None):
        filenames = []
        for o in self.outputs:
            if stats != None:
                stats.start_synthesis_comp(f"stateless {comp_name} {o}")
            # start with bound 1, since ALU cannot be a wire (which is bnd 0)
            bnd = 1
            # run Sketch
            sketch_filename = os.path.join(
                output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk")
            sketch_outfilename = os.path.join(
                output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk.out")
            f = open(sketch_filename, 'w+')
            self.write_grammar_ternary(f)
            self.write_sketch_spec_ternary(f, var_types, comp_name)
            f.write("\n")
            self.write_sketch_harness_ternary(f, var_types, comp_name)
            f.close()
            print("sketch {} > {}".format(
                sketch_filename, sketch_outfilename))
            f_sk_out = open(sketch_outfilename, "w+")
            print("running sketch, bnd = {}".format(bnd))
            print("sketch_filename", sketch_filename)
            ret_code = subprocess.call(
                ["sketch", sketch_filename], stdout=f_sk_out)
            print("return code", ret_code)
            if ret_code == 0:  # successful
                if stats != None:
                    stats.end_synthesis_comp(f"stateless {comp_name} {o}")
                print("solved")
                result_file = sketch_outfilename
                print("output is in " + result_file)
                filenames.append(result_file)
                break
            else:
                print("failed")
                assert(False)
            f_sk_out.close()
        return filenames

    def contains_ternary(self):
        for output in self.outputs:
            if is_branch_var(output):
                return True
        for input in self.inputs:
            if is_branch_var(input):
                return True
        for codelet in self.codelets:
            for var in codelet.get_defines():
                if is_branch_var(var):
                    return True
        return False

    def contains_only_ternary(self):
        for output in self.outputs:
            if not is_branch_var(output):
                return False
        return True

    # def write_sketch_file(self, output_path, comp_name, var_types, o, stats: test_stats.Statistics = None):  # o is the output
    #     if self.contains_ternary() and self.is_tofino:
    #         print('----------- writing ternary sketch file')
    #         return self.write_ternary_sketch_file(output_path, comp_name, var_types, stats)
    #     filename = ""
    #     if stats != None:
    #         stats.start_synthesis_comp(f"stateless {comp_name} {o}")
    #     # start with bound 1, since ALU cannot be a wire (which is bnd 0)
    #     bnd = 1
    #     while True:
    #         # run Sketch
    #         sketch_filename = os.path.join(
    #             output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk")
    #         sketch_outfilename = os.path.join(
    #             output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk.out")
    #         f = open(sketch_filename, 'w+')
    #         self.write_grammar(f)
    #         self.write_sketch_spec(f, var_types, comp_name, o)
    #         f.write("\n")
    #         self.write_sketch_harness(f, var_types, comp_name, o, bnd)
    #         f.close()
    #         print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
    #         f_sk_out = open(sketch_outfilename, "w+")
    #         print("running sketch, bnd = {}".format(bnd))
    #         print("sketch_filename", sketch_filename)
    #         ret_code = subprocess.call(
    #             ["sketch", sketch_filename], stdout=f_sk_out)
    #         print("return code", ret_code)
    #         if ret_code == 0:  # successful
    #             if stats != None:
    #                 stats.end_synthesis_comp(f"stateless {comp_name} {o}")
    #             print("solved")
    #             result_file = sketch_outfilename
    #             print("output is in " + result_file)
    #             filename = result_file
    #             break
    #         else:
    #             print("failed")

    #         f_sk_out.close()
    #         bnd += 1
    #     return filename


    def write_sketch_file(self, output_path, comp_name, var_types, o, synth_bounds, stats: test_stats.Statistics = None): # o is the output
        if self.contains_ternary() and self.is_tofino:
            print('----------- writing ternary sketch file')
            return self.write_ternary_sketch_file(output_path, comp_name, var_types, stats)
        filename = ""
        if stats != None:
            stats.start_synthesis_comp(f"stateless {comp_name} {o}")

        bnd_vars = self.get_input_bounds(synth_bounds)
        bnds_list = sorted(list(bnd_vars.keys()))
        min_bnd = min(bnds_list)
        succ_bnd = None # bound at which synthesis was successful

        bnd = min_bnd  # start with min bnd of inputs
        while True:
            # run Sketch
            sketch_filename = os.path.join(
                output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk")
            sketch_outfilename = os.path.join(
                output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk.out")
            f = open(sketch_filename, 'w+')
            # self.write_grammar(f)
            # self.write_weighted_grammar(f, synth_bounds)
            self.write_weighted_grammar_new(f, synth_bounds)
            self.write_sketch_spec(f, var_types, comp_name, o)
            f.write("\n")
            # self.write_sketch_harness(f, var_types, comp_name, o, bnd)
            # self.write_sketch_harness_weighted(f, var_types, comp_name, o, bnd, synth_bounds)
            self.write_sketch_harness_weighted_new(f, var_types, comp_name, o, bnd, synth_bounds)
            f.close()
            print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
            f_sk_out = open(sketch_outfilename, "w+")
            print("running sketch, bnd = {}".format(bnd))
            print("sketch_filename", sketch_filename)
            # ret_code = subprocess.call(["sketch", "--slv-parallel", sketch_filename], stdout=f_sk_out)
            ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
            print("return code", ret_code)
            if ret_code == 0:  # successful
                if stats != None:
                    stats.end_synthesis_comp(f"stateless {comp_name} {o}")
                print("solved")
                result_file = sketch_outfilename
                print("output is in " + result_file)
                filename = result_file
                break
            else:
                print("failed")

            f_sk_out.close()
            bnd += 1
        succ_bnd = bnd # record synthesis bound
        return (filename, succ_bnd)

    def get_input_bounds(self, synth_bounds):
        bnd_inputs = {} # bound -> inputs
        for i in self.inputs:
            assert(i in synth_bounds)
            bd = synth_bounds[i]
            if bd not in bnd_inputs:
                bnd_inputs[bd] = [i]
            else:
                bnd_inputs[bd].append(i)
            
        return bnd_inputs
        
class StatefulComponent(object):
    def __init__(self, stateful_codelet, grammar_name=None, is_tofino=True):
        self.codelet = stateful_codelet
        self.salu_inputs = {'metadata_lo': 0, 'metadata_hi': 0,
                            'register_lo': 0, 'register_hi': 0}
        self.isStateful = True
        # [stateful_codelet.state_var]
        self.state_vars = stateful_codelet.state_vars
        print('-------------------------------------- stateful codelet vars : ',
              self.state_vars, '--------------***')
        self.state_pkt_fields = stateful_codelet.get_state_pkt_field()
        self.comp_stmts = stateful_codelet.get_stmt_list()
        self.grammar_name = grammar_name
        self.is_tofino = is_tofino
        self.get_inputs_outputs()
        self.bci_inputs = []
        self.bci_outputs = []
        self.is_duplicated = False
        self.sort_inputs()

    # returns stringified representation of stateful node
    # note this is not unique as there can be parallel stateful nodes
    # after split_SCC_graph in dependencyGraph.py.
    def get_code_as_string(self):
        return self.codelet.get_code_as_string()

    def get_stateful_output(self):
        return self.codelet.get_stateful_output()

    def mark_as_duplicate(self):
        self.is_duplicated = True

    def add_bci_inputs(self, ins):
        self.bci_inputs += ins

    def add_bci_outputs(self, outs):
        self.bci_outputs += outs

    def set_name(self, name):
        self.name = name

    def get_inputs_outputs(self):
        self.inputs = self.codelet.get_inputs()
        self.outputs = self.codelet.get_defines()
        self.sort_inputs()

    # state vars need to come first.
    def sort_inputs(self):
        stateful_inputs = []
        stateless_inputs = []
        for input in self.inputs:
            if input in self.state_vars:
                stateful_inputs.append(input)
            else:
                stateless_inputs.append(input)
        stateful_inputs.sort()
        stateless_inputs.sort()
        self.inputs = stateful_inputs + stateless_inputs

    def temp_var(self, var):
        if var in self.state_pkt_fields:
            return True
        elif is_branch_var(var):
            return True
        else:
            return False

    def last_ssa_var(self, var):
        ssa_vars = [o for o in self.outputs if o !=
                    var and is_same_var(o, var)]
        if len(ssa_vars) == 0:
            return True  # var is the only SSA variable
        var_name = get_variable_name(var, ssa_vars[0])
        ssa_indices = [int(v.replace(var_name, '')) for v in ssa_vars]
        max_index = max(ssa_indices)
        var_index = int(var.replace(var_name, ''))

        return var_index > max_index

    def update_outputs(self, adj_comps):
        '''
        Keep output o if
        1. It is the state variable, OR
        2. It is used in an adjacent component, OR
        3. It is a packet field
        Allow an additional packet field / state var to be an output
        With merging, there can be at most 2 outputs (state_var and additional packet field / state var)
        TODO: ruijief: I see the issue here --- we can't
                use variable names (e.g. self.last_ssa_var(o)) to distinguish whether a thing is a stateful var or not
                anymore.
        '''
        redundant_outputs = []
        adj_inputs = [i for c in adj_comps for i in c.inputs]
        print("adj_inputs", adj_inputs)

        for o in self.outputs:
            if o not in self.state_vars:
                if o not in adj_inputs:  # not used in adjacent component
                    redundant_outputs.append(o)
                    # print("Redundant output: {}".format(o))

        print("redundant outputs", redundant_outputs)
        print("state_var", self.state_vars)

        for red_o in redundant_outputs:
            self.outputs.remove(red_o)

        self.create_used_state_vars(adj_comps)
        self.create_actual_outputs(adj_comps)

    def create_used_state_vars(self, adj_comps: list):
        used_state_vars = set()
        for c in adj_comps:
            for i in c.inputs:
                if i in self.state_vars:
                    used_state_vars.add(i)
        self.used_state_vars = list(used_state_vars)

    def create_actual_outputs(self, adj_comps: list):
        outputs = set()
        for c in adj_comps:
            for i in c.outputs:
                outputs.add(i)

        self.actual_outputs = outputs

    def get_input_bounds(self, synth_bounds):
        bnd_inputs = {} # bound -> inputs
        print("synth_bounds", synth_bounds)
        for i in self.inputs:
            print(i)
            if i in synth_bounds:
                bd = synth_bounds[i]
                if bd not in bnd_inputs:
                    bnd_inputs[bd] = [i]
                else:
                    bnd_inputs[bd].append(i)
            else:
                print("{} not in synth_bounds!".format(i)) # This should only happen for state vars
        
        return bnd_inputs

    def merge_component(self, comp, reversed=False):
        print("merge component: component is ---- ", self)
        print(' ********************** adding statements from component ',
              comp, ' with *************************')
        print(comp.comp_stmts)
        if reversed:
            self.codelet.add_stmts_before(comp.comp_stmts)
        else:
            self.codelet.add_stmts(comp.comp_stmts)

        # update comp_stmts
        self.comp_stmts = self.codelet.get_stmt_list()

        if comp.isStateful:
            if len(self.state_vars) > 1:
                print(
                    "Cannot merge stateful component (current component already has 2 state variables)")
                assert(False)
            print(' --my stateful vars: ', self.state_vars)
            print(' --their stateful vars: ', comp.state_vars)
            assert(len(comp.state_vars) == 1)
            self.state_vars.append(comp.state_vars[0])
            # get_state_pkt_field() returns a list
            self.state_pkt_fields += (comp.codelet.get_state_pkt_field())

        self.get_inputs_outputs()  # update inputs, outputs
        # state vars are always inputs
        # NOTE: There would be no need to add state vars as inputs explicitly if a codelet could have 2 state vars
        for s_var in self.state_vars:
            if s_var not in self.inputs:
                self.inputs.append(s_var)

    def set_alu_inputs(self):
        if len(self.inputs) > 4:
            print("Error: stateful update does not fit in the stateful ALU.")
            print('node: ', str(self))
            print('inputs: ', self.inputs)
            print('outputs: ', self.outputs)
            exit(1)

        print("~~~~~~~~~~set_alu_inputs: ", self.inputs)
        print(" ~~~| state var: ", self.state_vars)
        self.salu_inputs['register_lo'] = 0
        self.salu_inputs['register_hi'] = 0
        self.salu_inputs['metadata_lo'] = 0
        self.salu_inputs['metadata_hi'] = 0
        self.input_statevars = set()
        self.input_stateless_vars = set()
        for i in self.inputs:
            if i in self.state_vars:
                self.input_statevars.add(i)
                if self.salu_inputs['register_lo'] == 0:
                    self.salu_inputs['register_lo'] = i
                elif self.salu_inputs['register_hi'] == 0:
                    self.salu_inputs['register_hi'] = i
                else:
                    print(
                        "Error: Cannot have > 2 state variables in a stateful ALU. Component: ", str(self))
                    print(' problematic inputs: ', self.inputs)
                    print(' problematic state vars: ', self.state_vars)
                    assert(False)
            else:
                self.input_stateless_vars.add(i)
                if self.salu_inputs['metadata_lo'] == 0:
                    self.salu_inputs['metadata_lo'] = i
                elif self.salu_inputs['metadata_hi'] == 0:
                    self.salu_inputs['metadata_hi'] = i
                else:
                    print(
                        "Error: Cannot have > 2 metadata fields in a stateful ALU. Component: ", str(self))
                    print(' problematic inputs: ', self.inputs)
                    print(' problematic state vars: ', self.state_vars)
                    assert(False)

        print("salu_inputs", self.salu_inputs)

    def write_grammar(self, f):
        try:
            f_grammar = open(grammar_util.resolve_stateful(self.grammar_name))
            # copy gramar
            lines = f_grammar.readlines()
            for l in lines:
                f.write(l)

        except IOError:
            print("Failed to open stateful grammar file {}.".format(
                self.grammar_name))
            exit(1)

    def write_domino_sketch_spec(self, f, var_types, comp_name):
        # generate list of arguments
        self.sort_inputs()
        self.state_vars.sort()
        input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
        spec_name = comp_name
        # write function signature
        num_rets = grammar_util.num_statefuls_domino[self.grammar_name] + 1
        num_statefuls = grammar_util.num_statefuls_domino[self.grammar_name]
        f.write("int[{}] {}({})".format(
            num_rets, spec_name, ", ".join(input_types)) + "{\n")
        # declare output array
        spec_ret = "_out"
        f.write("\tint[{}] {};\n".format(num_rets, spec_ret))
        # declare defined variables
        defines = self.codelet.get_defines()
        for v in defines:
            if v not in self.inputs:
                f.write("\t{} {};\n".format(var_types[v], v))
        # function body
        for stmt in self.comp_stmts:
            f.write("\t{}\n".format(stmt.get_stmt()))

        # update output array
        si = 0

        for state_var in self.state_vars:
            f.write("\t{}[{}] = {};\n".format(spec_ret, si, state_var))
            si += 1

        while si < num_statefuls:
            f.write("\t{}[{}] = 0;\n".format(spec_ret, si))
            si += 1

        if self.codelet.stateful_output != None:
            f.write("\t{}[{}] = {};\n".format(
                spec_ret, si, self.codelet.stateful_output))
            si += 1
        else:
            f.write("\t{}[{}] = 0;\n".format(spec_ret, si))
            si += 1

        while si < num_rets:
            f.write("\t{}[{}] = 0;\n".format(spec_ret, si))
            si += 1

        # return
        f.write("\treturn {};\n".format(spec_ret))
        f.write("}\n")

    def write_tofino_sketch_spec(self, f, var_types, comp_name):
        input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
        spec_name = comp_name
        # write function signature
        f.write("int[3] {}({})".format(
            spec_name, ", ".join(input_types)) + "{\n")
        # declare output array
        output_array = "_out"
        f.write("\tint[3] {};\n".format(output_array))
        # declare defined variables
        defines = self.codelet.get_defines()
        for v in defines:
            if v not in self.inputs:
                f.write("\t{} {};\n".format(var_types[v], v))
        # function body
        for stmt in self.comp_stmts:
            f.write("\t{}\n".format(stmt.get_stmt()))
        # update output array

        f.write("\t{}[0] = {};\n".format(output_array, self.state_vars[0]))
        if len(self.state_vars) > 1:
            f.write("\t{}[1] = {};\n".format(output_array, self.state_vars[1]))
        else:
            f.write("\t{}[1] = 0;\n".format(output_array))

        if self.codelet.stateful_output != None:
            f.write("\t{}[2] = {};\n".format(
                output_array, self.codelet.stateful_output))
        else:
            f.write("\t{}[2] = 0;\n".format(output_array))
        """
        found_output = False
        for o in self.outputs:
            if o != self.salu_inputs[0] and o != self.inputs[1]:
                found_output = True
                f.write("\t{}[2] = {};\n".format(output_array, o))
        if not found_output:  # return state var
            f.write("\t{}[2] = 0;\n".format(output_array))
        """

        # return
        f.write("\treturn {};\n".format(output_array))
        f.write("}\n")

    def write_tofino_sketch_harness(self, f, var_types, comp_name):
        f.write("harness void sketch(")
        if len(self.inputs) >= 1:
            var_type = var_types[self.inputs[0]]
            f.write("{} {}".format(var_type, self.inputs[0]))

        for v in self.inputs[1:]:
            var_type = var_types[v]
            f.write(", ")
            f.write("{} {}".format(var_type, v))

        f.write(") {\n")

        f.write("\tint[3] impl = salu({}, {}, {}, {});\n".format(
                self.salu_inputs['metadata_lo'], self.salu_inputs['metadata_hi'], self.salu_inputs['register_lo'], self.salu_inputs['register_hi']
                ))
        f.write("\tint [3] spec = {}({});\n".format(
            comp_name, ', '.join(self.inputs)))

        f.write("\tassert(impl[0] == spec[0]);\n")
        f.write("\tassert(impl[1] == spec[1]);\n")
        f.write("\tassert(impl[2] == spec[2]);\n")
        f.write("}\n")

    def write_domino_sketch_harness(self, f, var_types, comp_name):
        self.sort_inputs()
        self.state_vars.sort()
        f.write("harness void sketch(")
        if len(self.inputs) >= 1:
            var_type = var_types[self.inputs[0]]
            f.write("{} {}".format(var_type, self.inputs[0]))

        for v in self.inputs[1:]:
            var_type = var_types[v]
            f.write(", ")
            f.write("{} {}".format(var_type, v))

        f.write(") {\n")

        num_outputs = grammar_util.num_outputs[self.grammar_name] + 1

        print("number of outputs for ", self.grammar_name, ": ", num_outputs)

        f.write('\t int[{}] impl = salu('.format(num_outputs))

        num_statefuls = grammar_util.num_statefuls_domino[self.grammar_name]
        num_stateless = grammar_util.num_stateless_domino[self.grammar_name]

        stateful_inputs = []
        stateless_inputs = []
        for input in self.inputs:
            if input in self.state_vars:
                stateful_inputs.append(input)
            else:
                stateless_inputs.append(input)
        
        if len(stateful_inputs) < num_statefuls:
            for _ in range(num_statefuls - len(stateful_inputs)):
                stateful_inputs.append('0')
        
        if len(stateless_inputs) < num_stateless:
            for _ in range(num_stateless - len(stateless_inputs)):
                stateless_inputs.append('0')
        
        f.write(','.join(stateful_inputs) + ',')
        f.write(','.join(stateless_inputs) + ');\n')

        f.write("\tint[{}] spec = {}({});\n".format(
            str(num_outputs), comp_name, ', '.join(self.inputs)))
        for i in range(num_outputs):
            f.write("\tassert(impl[{}] == spec[{}]);\n".format(str(i), str(i)))
        f.write("}\n")

    def write_sketch_file(self,
                          output_path, comp_name, var_types, prefix="", stats: test_stats.Statistics = None):
        #make sure stateful inputs appear before stateless ones.
        self.sort_inputs()
        if stats != None:
            stats.start_synthesis_comp(f"stateful {comp_name}")
        sketch_filename = os.path.join(
            output_path, prefix + f"{comp_name}_stateful.sk")
        sketch_outfilename = os.path.join(
            output_path, prefix + f"{comp_name}_stateful.sk" + ".out")
        f = open(sketch_filename, 'w+')
        self.set_alu_inputs()
        self.write_grammar(f)
        if self.is_tofino:
            self.write_tofino_sketch_spec(f, var_types, comp_name)
            f.write("\n")
            self.write_tofino_sketch_harness(f, var_types, comp_name)
        else:
            self.write_domino_sketch_spec(f, var_types, comp_name)
            f.write('\n')
            self.write_domino_sketch_harness(f, var_types, comp_name)

        f.close()
        print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
        with open(sketch_outfilename, "w+") as f_sk_out:
            print("running sketch for stateful")
            print("sketch_filename", sketch_filename)
            ret_code = subprocess.call(
                ["sketch", sketch_filename], stdout=f_sk_out)
            print("return code", ret_code)
            if ret_code == 0:  # successful
                if stats != None:
                    stats.end_synthesis_comp(f"stateful {comp_name}")
                print("solved")
                result_file = sketch_outfilename
                print("output is in " + result_file)
                return result_file
            else:
                print("failed")
                return None

    def print(self):
        stmts = self.codelet.get_stmt_list()
        for s in stmts:
            s.print()

    def __str__(self):
        return " ".join(s.get_stmt() for s in self.codelet.stmt_list)


class Synthesizer:
    def __init__(self, state_vars,
                 var_types, pkt_vars, PIs, dep_graph, read_write_flanks, stateful_nodes,
                 filename, p4_output_name, enableMerging, stats: test_stats.Statistics = None,
                 is_tofino=True, stateless_path=None, stateful_path=None, eval = False):
        # handle domino grammar generation.
        self.is_tofino = is_tofino
        self.stateless_path = stateless_path
        self.stateful_path = stateful_path

        self.eval = eval

        self.state_vars = state_vars
        self.var_types = var_types
        self.PIs = PIs
        self.pkt_vars = pkt_vars

        self.filename = filename
        self.templates_path = "templates"
        self.output_dir = filename
        self.stats = stats

        self.enableMerging = enableMerging

        self.synth_bounds = {} # key: variable, value: bound at which synthesis succeeded (represents earliest stage variable can be used)
        for v in self.PIs:
            self.synth_bounds[v] = 0

        print("synth_bounds", self.synth_bounds)

        try:
            os.mkdir(self.output_dir)
        except OSError:
            print("Output directory {} could not be created".format(self.output_dir))
        else:
            print("Created output directory {}".format(self.output_dir))

        self.dep_graph = dep_graph  # scc_graph in DependencyGraph
        self.read_write_flanks = read_write_flanks
        self.stateful_nodes = stateful_nodes
        self.components = []

        print("Synthesizer")
        print("output dir", self.output_dir)

        self.get_rw_flanks()

        self.process_graph()
        return
        """
        if self.stats != None:
            self.stats.start_synthesis()

        self.do_synthesis()
        if is_tofino:
            self.synth_output_processor.postprocessing()
            if self.stats != None:
                self.stats.end_synthesis()
            print(self.synth_output_processor.to_ILP_str(table_name="NewTable"))
        else:
            self.synth_output_processor.postprocessing()
            if self.stats != None:
                self.stats.end_synthesis()
                print("Domino synthesis: ended successfully.")

            for alu in self.synth_output_processor.dependencies:
                print("ALU: ")
                alu.print()
                print("----------------")
                alus = self.synth_output_processor.dependencies[alu]
                for adj_alu in alus:
                    print(" --> adjacent alu: ")
                    adj_alu.print()
                print("----------------")
            exit(1)
        """

    def get_rw_flanks(self):
        rw_flanks = self.read_write_flanks  # dictionary
        self.rw_flank_vars = set()
        for state_var, rw_stmts in rw_flanks.items():
            r_stmt = rw_stmts["read"]
            w_stmt = rw_stmts["write"]
            self.rw_flank_vars.add(r_stmt.state_pkt_field_init)
            self.rw_flank_vars.add(w_stmt.state_pkt_field_final)
        print("Stored read, write flank variables")
        print(self.rw_flank_vars)

    def get_var_type(self, v):
        if v in self.var_types:
            return self.var_types[v]
        else:
            print("v", v)
            assert("[" in v)  # array access
            array_name = v[:v.find("[")]
            assert(array_name in self.var_types)
            return self.var_types[array_name]

    # returns True iff merging a, b increases depth of DAG by 1.
    # this is a symmetric condition.
    def merging_increases_depth(self, a, b):
        # import graphutil
        # return (graphutil.merge_increases_depth(a, b))
        # XXX: Since we implement predecessor packing check, we skip this for now.
        return False

    # calls sketch to determine if component A+B is synthesizeable.
    # Note: a is always predecessor of b. a --> b

    def try_merge(self, a, b):
        print('try_merge: trying to merge components: ')
        print(' | a: ', a)
        print(' | b: ', b)
        if a.isStateful:
            print(' | state_pkt_fields of component a: ', a.state_pkt_fields)
        if b.isStateful:
            print(' | state_pkt_fields of component b: ', b.state_pkt_fields)
        if a.isStateful:
            new_comp = copy.deepcopy(a)
            new_comp.merge_component(b)
        else:
            new_comp = copy.deepcopy(b)
            new_comp.merge_component(a, True)

        #new_comp.update_outputs(self.comp_graph.neighbors(b))
        print('resultant component: ')
        print(new_comp)
        #print('new component inputs: ', new_comp.inputs)
        #print('new component outputs: ', new_comp.outputs)
        #print('new component state_pkt_fields: ', new_comp.state_pkt_fields)

        # Case 1: a, b both stateful. Output is b.stateful_output
        # Case 2: a stateless, b stateful. Output is b.stateful_output
        if b.isStateful:
            # handles both case 1, 2
            new_comp.codelet.stateful_output = b.codelet.stateful_output
            """ TODO: we can potentially not duplicate a node if b is sink and a writes out to a packet field.
            if b.codelet.stateful_output != None:
                new_comp.codelet.stateful_output = b.codelet.stateful_output
            else: 
                # b is sink. So use output of a.
                if a.isStateful and a.stateful_output != None and a.stateful_output not in self.rw_flank_vars and not is_tmp_var(a.stateful_output):
                    new_comp.codelet.stateful_output = a.codelet.stateful_output
                elif not is_tmp_var(a.codelets[0].stmt_list[0].lhs): # TODO: get more granular than this --- intermediate packet fields are also temp.
                    new_comp.codelet.stateful_output = a.codelets[0].stmt_list[0].lhs
            """
        else:
            # Case 3: b stateless. Output is b.codelets[0].stmt_list[0].lhs
            new_comp.codelet.stateful_output = b.codelets[0].stmt_list[0].lhs

        print('-------------- Merging... -------------')
        # try:
        result = new_comp.write_sketch_file(self.output_dir, 'query_' + str(self.merge_idx), self.var_types,
                                            prefix='try_merge_')
        self.merge_idx += 1
        if result == None:
            print('---------- Merge failure. ---------')
            return False
        else:
            print('---------- Merge success. ---------')
            return True
        # except:
        #	print('AssertionError? failed ')
        #	print('---------- Merge failure. ---------')
        #	return False

    def non_temporary_outputs(self, comp):
        x = list(
            filter(lambda x: not self.var_types[x] == 'bit', comp.outputs))
        print('                 * non_temp_outs(', str(comp), '): ', x)
        return x

    def exclude_read_write_flanks(self, comp, filter_temporaries=True):
        successors = self.comp_graph.successors(comp)
        succ_inputs = set()
        for succ in successors:
            succ_inputs.update(succ.inputs)
        print(' exclude_read_write_flanks: successor inputs: ', succ_inputs)
        curr_outputs = set(comp.outputs)
        filtered_outputs = list(curr_outputs.intersection(succ_inputs))
        if filter_temporaries:
            filtered_outputs = list(
                filter(lambda x: not self.var_types[x] == 'bit', filtered_outputs))
            print(' exclude_read_write_flanks: filtered outputs (temp filtered): ',
                  filtered_outputs)
        else:
            print(' exclude_read_write_flanks: filtered outputs (temp unfiltered): ',
                  filtered_outputs)

        return filtered_outputs

    def pred_is_branch(self, comp):
        preds = list(self.comp_graph.predecessors(comp))
        return len(preds) == 1 and ((not preds[0].isStateful) and preds[0].contains_ternary())

    def merge_candidate(self, a, b):
        a.update_outputs(self.comp_graph.neighbors(a))
        b.update_outputs(self.comp_graph.neighbors(b))
        # PRECONDITION: a has to be predecesssor of b,
        # i.e. a-->b is an edge.
        # returns True if components A and B are valid merge candidates.
        # Two components are stateless. Return false.
        if not (a.isStateful or b.isStateful):  # if a and b are both stateless, return
            print('    ~ merge_candidate: both components are stateless.')
            return False

        # Check for predecessor packing condition.
        if len(list(self.comp_graph.successors(a))) != 1:
            print('    ~ merge_candidate: predecessor packing condition not met.')
            return False
        # else:
        #	assert list(self.comp_graph.successors(a))[0] == b

        # self.exclude_read_write_flanks(a, filter_temporaries=False)
        merged_output_vars = set(a.outputs)
        # self.exclude_read_write_flanks(b, filter_temporaries=False)
        merged_output_vars.update(b.outputs)
        # now merged_output_vars contains both a and b's outputs, deduplicated.
        # vars needed post-merge. Since succ(a) = {b}, only vars needed are b's out-neighbors' inputs.
        b_succ_inputs = set()
        for b_succ in self.comp_graph.successors(b):
            b_succ_inputs.update(b_succ.inputs)

        output_vars = set()
        for x in merged_output_vars:
            if x in b_succ_inputs or (not is_tmp_var(x) and not (x in self.rw_flank_vars)):
                output_vars.add(x)

        merged_output_vars = list(output_vars)

        if len(merged_output_vars) > 2:
            print(
                '		~ merge_candidate: cannot merge a and b because too many output variables.')
        #
        #  check inputs size
        #
        # since a-->b, we filter inputs to b that are a's outputs.
        merged_inputs = set(a.inputs)
        merged_inputs.update(b.inputs)
        merged_inputs = list(merged_inputs)
        merged_inputs = list(
            filter(lambda x: x not in a.outputs, merged_inputs))
        print('     | merged inputs: ', merged_inputs)

        merged_state_vars = set()
        if a.isStateful:
            merged_state_vars.update(a.state_vars)
        if b.isStateful:
            merged_state_vars.update(b.state_vars)
        merged_stateless_vars = list(
            filter(lambda x: x not in merged_state_vars, merged_inputs))
        print('		| merged state vars: ', merged_state_vars)
        print('		| merged stateless vars: ', merged_stateless_vars)
        if len(merged_state_vars) > 2 or len(merged_stateless_vars) > 2:
            print(' 	| cannot merge: too many inputs.')
            return False
        else:
            print('		| merge_candidate: Can try merging.')
            return True

    def perform_merge(self, a, b):
        # actually merge two components (a, b) into one.
        # a is pred. This is mainly to see which direction we do the merge.
        print('perform_merge: merging components :')
        print(' | component a: ', a)
        print(' | component b: ', b)
        if a.isStateful:
            print(' | state_pkt_fields of component a: ', a.state_pkt_fields)
        if b.isStateful:
            print(' | state_pkt_fields of component b: ', b.state_pkt_fields)

        if a.isStateful:
            new_comp = copy.deepcopy(a)
            new_comp.merge_component(b)
        else:  # b must be a stateful comp
            new_comp = copy.deepcopy(b)
            new_comp.merge_component(a, True)

        # Case 1: a, b both stateful. Output is b.stateful_output
        # Case 2: a stateless, b stateful. Output is b.stateful_output
        if b.isStateful:
            # handles both case 1, 2
            new_comp.codelet.stateful_output = b.codelet.stateful_output
            """ TODO: we can potentially not duplicate a node if b is sink and a writes out to a packet field.
            if b.codelet.stateful_output != None:
                new_comp.codelet.stateful_output = b.codelet.stateful_output
            else: 
                # b is sink. So use output of a.
                if a.isStateful and a.stateful_output != None and a.stateful_output not in self.rw_flank_vars and not is_tmp_var(a.stateful_output):
                    new_comp.codelet.stateful_output = a.codelet.stateful_output
                elif not is_tmp_var(a.codelets[0].stmt_list[0].lhs): # TODO: get more granular than this --- intermediate packet fields are also temp.
                    new_comp.codelet.stateful_output = a.codelets[0].stmt_list[0].lhs
            """
        else:
            # Case 3: b stateless. Output is b.codelets[0].stmt_list[0].lhs
            new_comp.codelet.stateful_output = b.codelets[0].stmt_list[0].lhs

        # create new merged component, add edges
        self.comp_graph.add_node(new_comp)
        self.comp_graph.add_edges_from([(x, new_comp)
                                       for x in self.comp_graph.predecessors(a)])
        self.comp_graph.add_edges_from([(new_comp, y)
                                       for y in self.comp_graph.successors(b)])

        # remove two old components
        print("removing two old components")
        self.comp_graph.remove_node(a)
        self.comp_graph.remove_node(b)

        new_comp.update_outputs(self.comp_graph.neighbors(new_comp))
        print('		* new component : ', new_comp)
        print('		* new component inputs : ', new_comp.inputs)
        print('		* new component outputs : ', new_comp.outputs)
        print('		* state_pkt_fields of new component: ',
              new_comp.state_pkt_fields)
        return new_comp

    def reverse_top_order(self):
        top = list(nx.topological_sort(self.comp_graph))
        top.reverse()
        return top

    def all_outputs_temp(self, comp):
        for o in comp.outputs:
            if (not is_tmp_var(o)) and (o not in self.rw_flank_vars):
                return False
        return True

    # decide if any of (a --> b) requires duplicate.
    # Note that a only goes into b.
    # precondition: synthesis query succeeds.
    def pred_needs_duplicate(self, a, b):

        # TODO: This requires more careful handling. (See above about when b is sink). For now we omit it.
        # # Initially: if b is sink, then no need to duplicate a.
        # if b.isStateful and b.codelet.stateful_output == None:
        #	return False

        # Case I: a, b both stateful.
        if a.isStateful and b.isStateful:
            return False
        # Case II: a is stateless, b is stateful.
        if (not a.isStateful) and b.isStateful:
            # note this is conservative --- need preprocessor input to determine last_ssa_var.
            if not is_tmp_var(a.codelets[0].stmt_list[0].lhs) and (a.codelets[0].stmt_list[0].lhs not in self.rw_flank_vars):
                return True
            else:  # is temporary var. return false.
                return False
        # Case III: a is stateful, b is stateless.
        if a.isStateful and (not b.isStateful):
            if a.codelet.stateful_output != None:
                if (not is_tmp_var(a.codelet.stateful_output)) and (a.codelet.stateful_output not in self.rw_flank_vars):
                    return True
            else:
                return False

    def recursive_merge(self):
        nodes = self.reverse_top_order()
        print(' * recursive_merge strategy: nodes ordered ',
              list(map(lambda x: str(x), nodes)))
        for node in nodes:
            if not (node in self.merge_processed):
                halt = False
                merged_component = None
                print(' * recursive_merge: node :: ', node)
                print(' node outputs: ', node.outputs)
                print(' node inputs: ', node.inputs)
                self.exclude_read_write_flanks(node)
                for pred in self.comp_graph.predecessors(node):
                    print('  - recursive_merge: looking at preds of ', node)
                    print('     | ', pred)
                    if self.merge_candidate(pred, node) and not(pred.is_duplicated) and not(node.is_duplicated):
                        # try calling sketch to synthesize new component.
                        if self.try_merge(pred, node):
                            print(' mergeing two components...')
                            # merging successful.

                            # store predecessors of predecessor.
                            predpreds = list(
                                self.comp_graph.predecessors(pred))
                            # whether predecessor needs duplicating?
                            pred_needs_dup = self.pred_needs_duplicate(
                                pred, node)

                            self.merge_processed.add(pred)
                            self.merge_processed.add(node)
                            # perform_merge deletes pred, node
                            merged_component = self.perform_merge(pred, node)

                            if pred_needs_dup:
                                print("duplicating predecessor.... ")
                                pred.mark_as_duplicate()
                                print(pred)
                                self.comp_graph.add_node(pred)
                                for np in predpreds:
                                    self.comp_graph.add_edge(np, pred)

                            if self.stats != None:
                                self.stats.incr_num_successful_merges()
                            self.recursive_merge()
                            halt = True
                        else:
                            print('   | synthesis query failed. Not merging.')
                            print('   | number of nodes in comp_graph: ',
                                  len(self.comp_graph.nodes))
                    else:
                        print('     | not a merge candidate.')
                    if halt:
                        break
                print(' * recursive_merge: finished processing ', node)
                if merged_component != None:
                    self.merge_processed.add(merged_component)
                else:
                    self.merge_processed.add(node)

    def merge_components(self):
        self.merge_processed = set()
        self.recursive_merge()

    # TODO: this is a kludge for now: we need to properly
    # do BFS in order to deduplicate the nodes we return.
    # for now we use the list(set(...)) trick in code that
    # calls this method to dedup.
    #
    # return format: (BCI codelets, inputs to this component)
    def BCI(self, codelet):
        if codelet.is_stateful(self.state_vars):
            return [], [codelet]
        ret = []
        ret_inputs = []
        for pred in self.dep_graph.predecessors(codelet):
            pred_ret, pred_inputs = self.BCI(pred)
            ret += pred_ret
            ret_inputs += pred_inputs
        ret.append(codelet)
        return ret, ret_inputs  # TODO: deduplicate

    # Draws a scc_graph

    def draw_graph(self, graph, graphfile):
        dot = Digraph(comment='Component graph')
        node_stmts = {}
        idx = 0
        for node in graph.nodes:
            if node.isStateful:
                stmt_text = str(idx) + "; " + str(node)
                if node.codelet.stateful_output != None:
                    stmt_text += " [stateful output=" + \
                        node.codelet.stateful_output + "]"
                stmt_text = stmt_text.replace(":", "|")
                node_stmts[node] = stmt_text
                dot.node(stmt_text)
                idx += 1
            else:
                stmt_text = str(idx) + '; ' + str(node)
                stmt_text = stmt_text.replace(":", "|")
                node_stmts[node] = stmt_text
                dot.node(stmt_text)
                idx += 1

        if not self.eval:
            print('total number of nodes created: ', idx)
            for (u, v) in graph.edges:
                dot.edge(node_stmts[u], node_stmts[v])
            dot.render(graphfile, view=True)

    def compute_scc_graph(self):
        # Step 1: Process stateful components. By processing we mean
        # forming a graph of stateful singleton components.
        i = 0
        # maps the string of each stateful codelet to the component it belongs to.
        codelet_component = {}
        # component -> list of codelets that are inputs to that component.
        component_inputs = {}
        for u in self.stateful_nodes:
            u.is_stateful(self.state_vars)  # initialize state_vars in u
            if self.stateful_path != None:
                stateful_comp = StatefulComponent(
                    u, grammar_name=self.stateful_path, is_tofino=self.is_tofino)
            else:
                stateful_comp = StatefulComponent(u, is_tofino=self.is_tofino)
            stateful_comp.set_name('comp_' + str(i))
            print('compute_scc_graph: StatefulComponent(', stateful_comp.name,
                  '): state vars: ', stateful_comp.state_vars)
            self.components.append(stateful_comp)
            codelet_component[str(u)] = stateful_comp
            i += 1

        # Step 2: Add single codelets as stateless nodes

        for codelet in self.dep_graph.nodes:
            if not (codelet.is_stateful(self.state_vars)):
                stateless_comp = Component(
                    [codelet], i, grammar_name=self.stateless_path, is_tofino=self.is_tofino)
                self.components.append(stateless_comp)
                codelet_component[str(codelet)] = stateless_comp
                stateless_comp.set_name('comp_' + str(i))
                i += 1

        # Step 3: build graph
        self.scc_graph = nx.DiGraph()
        for comp in self.components:
            self.scc_graph.add_node(comp)
            if comp.isStateful:
                for u in self.dep_graph.predecessors(comp.codelet):
                    u_comp = codelet_component[str(u)]
                    self.scc_graph.add_edge(u_comp, comp)
            else:  # comp is stateless
                for u in self.dep_graph.predecessors(comp.codelets[0]):
                    u_comp = codelet_component[str(u)]
                    self.scc_graph.add_edge(u_comp, comp)

        print('number of nodes on SCC_GRAPH: ', len(self.scc_graph.nodes))

        self.draw_graph(self.scc_graph, self.filename + "_scc_graph")

        # After building graph, for each stateful node, check if there are predecessor nodes that contain
        # logic dependant only on current node's other input that can be folded into current node
        self.comp_graph = self.scc_graph

        def partition_stateful_predecessors(preds):
            node_to_flanks = {}
            for node in preds:
                str_node = node.get_code_as_string()
                if str_node in node_to_flanks:
                    if node.codelet.stateful_output != None:
                        stateful_output = node.codelet.stateful_output 
                        node_to_flanks[str_node].add((node, stateful_output, (node.codelet.get_stmt_of(stateful_output))))
                else:
                    if node.codelet.stateful_output == None:
                        node_to_flanks[str_node] = set(), node
                    else:
                        stateful_output = node.codelet.stateful_output
                        node_to_flanks[str_node] = set([(node, stateful_output, (node.codelet.get_stmt_of(stateful_output)))])
            return node_to_flanks

        #for comp in self.components:
        #    if comp.isStateful:
        #        print('curr node: ', str(comp))
        #        print('-------------------------')
        #        print(partition_stateful_predecessors(list(filter(lambda x: x.isStateful, self.scc_graph.predecessors(comp)))))
        #        print('-------------------------')

        # we set merge_idx to a high number to help discern these queries are made by
        # try_fold_pred when debugging.
        self.merge_idx = 100
        def try_fold_pred(comp, pred_stmts, pred):
            try_merge_pred_out = Component([Codelet(stmts=pred_stmts)],
                id = self.merge_idx, grammar_name=self.stateful_path, is_tofino = self.is_tofino)
            self.merge_idx += 1
            self.scc_graph.add_node(try_merge_pred_out)
            if self.try_merge(try_merge_pred_out, comp):
                print('can merge ', str(pred_stmts), ' into node ', str(comp))
                self.scc_graph.remove_node(try_merge_pred_out)
                self.scc_graph.remove_edge(pred, comp)
                comp.codelet.add_stmts_before(pred_stmts)
                comp.comp_stmts = comp.codelet.get_stmt_list()
                comp.get_inputs_outputs()
                return True
            else:
                print('...merge failed. continue iteration')
                self.scc_graph.remove_node(try_merge_pred_out)
                return False

        # try_fold_preds try to coalesce together many different predecessors 
        # that share the same primary input 
        def try_fold_preds(comp, pred_stmts, preds):
            try_merge_pred_out = Component([Codelet(stmts=pred_stmts)],
                id = self.merge_idx, grammar_name=self.stateful_path, is_tofino = self.is_tofino)
            self.merge_idx += 1
            self.scc_graph.add_node(try_merge_pred_out)
            if self.try_merge(try_merge_pred_out, comp):
                print('can merge ', str(pred_stmts), ' into node ', str(comp))
                self.scc_graph.remove_node(try_merge_pred_out)
                for pred in preds:
                    self.scc_graph.remove_edge(pred, comp)
                comp.codelet.add_stmts_before(pred_stmts)
                comp.comp_stmts = comp.codelet.get_stmt_list()
                comp.get_inputs_outputs()
                print(' merged component inputs: ', comp.inputs)
                return True
            else:
                print('...merge failed. continue iteration')
                self.scc_graph.remove_node(try_merge_pred_out)
                return False


        for comp in self.components:
            if comp.isStateful:
                if len(comp.inputs) > 2:
                    comp_inputs = set()
                    input_stmts = {}
                    input_deps = {}
                    input_pred = {}
                    for pred in self.comp_graph.predecessors(comp):
                        # get output of predecessor node
                        if pred.isStateful:
                            stateful_output = pred.codelet.stateful_output
                            if stateful_output != None:
                                comp_inputs.add(stateful_output)
                                dep_stmts, read_flanks, write_flanks = pred.codelet.get_stmt_deps(pred.codelet.get_stmt_of(stateful_output))
                                # if is write_flank, needs special logic to handle.
                                if dep_stmts == [] and read_flanks == [] and stateful_output == write_flanks[0]:
                                    print(' ***** found write flank ***** ', stateful_output)
                                    # here we treat write flank as dependant on the read flank.
                                    read_flank, bci = pred.codelet.get_write_flank_deps(stateful_output)
                                    print(' ** corresponding read_flank: ', read_flank)
                                    print(' * deps: ', bci)
                                    if read_flank != None:
                                        input_stmts[stateful_output] = bci 
                                        input_deps[stateful_output] = [read_flank]
                                        input_pred[stateful_output] = pred
                                    else:
                                        input_stmts[stateful_output] = dep_stmts 
                                        input_deps[stateful_output] = [stateful_output]
                                        input_pred[stateful_output] = pred
                                else:
                                    input_stmts[stateful_output] = dep_stmts
                                    input_deps[stateful_output] = read_flanks + write_flanks
                                    input_pred[stateful_output] = pred
                        else:
                            comp_inputs.add(pred.codelets[0].stmt_list[0].lhs)
                            input_stmts[pred.codelets[0].stmt_list[0].lhs] = pred.codelets[0].stmt_list
                            input_deps[pred.codelets[0].stmt_list[0].lhs] = pred.codelets[0].stmt_list[0].rhs_vars
                            input_pred[pred.codelets[0].stmt_list[0].lhs] = pred


                    # if all other predecessors depend on a single predecessor, try extracting their logic out into 
                    # current node and synthesize.
                    for primary_input in comp_inputs:
                        is_primary_input = True 
                        for input in comp_inputs:
                            if input != primary_input:
                                if input_deps[input] != [primary_input]:
                                    is_primary_input = False 
                                    print('input ', input, ' depends on ', input_deps[input], ' other than ', primary_input)
                        if is_primary_input:
                            print('primary input found: ', primary_input)
                            print('trying to merge all other inputs into current node and synthesize')
                            stmts = []
                            preds = []
                            print('comp inputs: ', comp.inputs)
                            for input in comp_inputs:
                                if input != primary_input:
                                    stmts += input_stmts[input]
                                    preds.append(input_pred[input])
                            try_fold_preds(comp, stmts, preds)
                            

        self.draw_graph(self.scc_graph, self.filename + "_pre_doctored")

        for comp in self.components:
            if comp.isStateful:
                comp.get_inputs_outputs()

                # try folding stateless predecessor nodes into stateful node to 
                # reduce number of inputs
                stateless_predecessors = list(filter(lambda x: not x.isStateful, self.scc_graph.predecessors(comp)))
                for pred in stateless_predecessors:
                    pred_stmt = pred.codelets[0].stmt_list[0]
                    other_inputs = set(comp.inputs)
                    other_inputs.remove(pred_stmt.lhs)
                    can_try_merge = True 
                    for rhs in pred_stmt.rhs_vars:
                        if rhs not in other_inputs:
                            can_try_merge = False 
                    if not can_try_merge:
                        continue # skip the current predecessor
                    print(' all rhs in other inputs, trying merge...')
                    # now we have confirmed that the output of pred
                    # is merely a dependency of some other input.
                    # we can now try remove dependency on pred and try 
                    # coalescing pred_output, pred_stmt into the current node.
                    try:
                        try_fold_pred(comp, [pred_stmt], pred)
                    except: continue # TODO

                # try folding stateful predecessor nodes into stateful node to 
                # reduce number of inputs. 
                # first, we partition the stateful predecessors into 
                # into sets of equivalent nodes with different output flanks
                # first, see if all other predecessors depends on single predecessor

                pred_to_flanks = partition_stateful_predecessors(list(filter(lambda x: x.isStateful, self.scc_graph.predecessors(comp))))                
                # iterate over each equivalence partition 
                for str_pred in pred_to_flanks:
                    # look at each (flank, pred) pair in the partition
                    # if the flank only depends on other inputs into current component,
                    # we can try safely remove the dependency on that flank as input and
                    # instead include the flank's statement in our synthesis scope.
                    for pred, pred_output, pred_stmt in pred_to_flanks[str_pred]:
                        assert (pred, comp) in self.scc_graph.edges
                        print('inputs: ', comp.inputs)
                        other_inputs = set(comp.inputs)
                        other_inputs.remove(pred_output)
                        pred_output_rhs_vars = set(pred_stmt.rhs_vars)
                        print('pred_stmt: ', str(pred_stmt))
                        print('pred rhs: ', pred_stmt.rhs_vars)
                        print('comp inputs: ', comp.inputs)
                        print('other inputs: ', other_inputs)
                        can_try_merge = True
                        for rhs in pred_output_rhs_vars:
                            if rhs not in other_inputs:
                                print(' rhs not in other inputs, continuing...')
                                can_try_merge = False # skip
                                break
                        if not can_try_merge:
                            continue
                        print(' all rhs in other inputs, trying merge...')
                        # now we have confirmed that the output of pred
                        # is merely a dependency of some other input.
                        # we can now try remove dependency on pred and try 
                        # coalescing pred_output, pred_stmt into the current node.
                        try: 
                            try_fold_pred(comp, [pred_stmt], pred)
                        except:
                            # failed. Continue iteration.
                            continue

        self.draw_graph(self.scc_graph, self.filename + "_doctored_graph")


        # Step 4: call merging procedure (if we choose to enable it)
        self.comp_graph = self.scc_graph

        print('number of nodes in comp_graph: ', len(self.comp_graph.nodes))

        self.merge_idx = 0
        if self.enableMerging:
                self.merge_components()

        self.draw_graph(self.comp_graph, self.filename + "_merged_graph")

        # fold branch temporaries
        # if merging is disabled, we don't run folding.
        folded_node = self.enableMerging
        folding_idx = 0
        while folded_node:
            print(' ----------------- iteratively folding node. folding_idx = ', folding_idx)
            folded_node = False
            folding_idx += 1
            for node in self.comp_graph.nodes:
                if node.isStateful:
                    preds = list(self.comp_graph.predecessors(node))
                    for pred in preds:
                        if (not pred.isStateful) and pred.contains_only_ternary():
                            # pred is br_tmp.
                            # We can try folding predecessor into current node and synthesize.
                            print('trying to fold node: ', str(node))
                            print('trying to fold predecessor: ', str(pred))

                            # check inputs
                            merged_inputs = set(pred.inputs)
                            merged_inputs.update(node.inputs)
                            merged_inputs = list(merged_inputs)
                            merged_inputs = list(filter(
                                lambda x: x not in pred.outputs and x not in self.state_vars, merged_inputs))

                            if self.is_tofino:
                                if len(merged_inputs) > grammar_util.num_stateless['tofino']:
                                    print(
                                        ' --- cannot fold. too many stateless inputs: ', merged_inputs)
                                    continue
                            else:
                                if len(merged_inputs) > grammar_util.num_stateless[self.stateful_path]:
                                    print(
                                        ' --- cannot fold. too many stateless inputs: ', merged_inputs)
                                    continue

                            if self.try_merge(pred, node):
                                print(' --- can fold. performing folding...')
                                folded_node = True
                                # add br_tmp statement into stateful node
                                node.codelet.add_stmts_before(
                                    pred.codelets[0].stmt_list)
                                node.comp_stmts = node.codelet.get_stmt_list()
                                # delete edge from pred to node
                                self.comp_graph.remove_edge(pred, node)
                                # inherit predecessor's in-edges
                                for predpred in self.comp_graph.predecessors(pred):
                                    self.comp_graph.add_edge(predpred, node)
                                node.get_inputs_outputs()

                            else:
                                print(' --- cannot fold.')

        self.draw_graph(self.comp_graph, self.filename + "_folded_graph")

        # all synthesized stateful outputs
        stateful_nodes = filter(lambda x: x.isStateful, self.comp_graph.nodes)
        stateful_outputs = list(
            map(lambda x: x.codelet.stateful_output, stateful_nodes))

        # create principal outputs
        self.principal_outputs = set()

        for codelet in self.dep_graph.nodes:
            if not(codelet.is_stateful(self.state_vars)):
                # if len(list(self.dep_graph.successors(codelet))) == 0:
                # contains principal outputs. Include it in the list
                # Except when it is synthesized as stateful output
                var = codelet.stmt_list[-1].lhs
                if var not in stateful_outputs \
                        and var in self.pkt_vars \
                and var not in self.rw_flank_vars:
                    self.principal_outputs.add(codelet.stmt_list[0].lhs)

        """
        # adding everything that isn't a flank var
        for var in self.pkt_vars:
            if var not in self.rw_flank_vars and var in self.var_types:
                self.principal_outputs.add(var)
        """

        # In addition to POs, we also need to synthethize inputs to stateful nodes.
        # add those as well.
        for node in self.comp_graph.nodes:
            if node.isStateful:
                # add stateless inputs of that node as POs.
                for pred in self.comp_graph.predecessors(node):
                    if not pred.isStateful:
                        pred_output = pred.codelets[0].stmt_list[0].lhs
                        if pred_output in node.inputs:
                            self.principal_outputs.add(pred_output)
        #        for node_input in node.inputs:
        #            if (node_input not in self.state_vars) and (node_input not in self.rw_flank_vars):
        #                self.principal_outputs.add(node_input)

        print('Principal Outputs: ', self.principal_outputs)


        # TODO: (preprocessor input) in addition to those above we also need to synthesize
        # last SSA'd packet fields. But can't do so without preprocessor input yet.

        print(self.principal_outputs)

        # Step 5: Build synthesis graph
        node_to_bci = {}
        bci_rooted_at = {}
        self.synth_graph = nx.DiGraph()

        for node in self.comp_graph.nodes:
            node_to_bci[node] = []

        # 5a) add all stateful nodes as usual
        for node in self.comp_graph.nodes:
            if node.isStateful:
                self.synth_graph.add_node(node)
                node_to_bci[node] = [node]

        # 5b) add BCIs to synthesis graph
        for node in self.comp_graph.nodes:
            if not node.isStateful and node.codelets[0].get_stmt_list()[0].lhs in self.principal_outputs:
                bci = nx.DiGraph()

                def getBCI(n, visited: set, bci: nx.DiGraph):
                    if n in visited or n.isStateful:
                        return []
                    else:
                        # visit predecessors
                        visited.add(n)
                        for p in self.comp_graph.predecessors(n):
                            if not p.isStateful:
                                bci.add_edge(p, n)
                                getBCI(p, visited, bci)
                bci.add_node(node)  # corner case
                getBCI(node, set(), bci)
                linearized_bci = list(nx.topological_sort(bci))
                # linearized_bci contains a number of components, each containing a codelet.
                # map it to a single component and synthesize.
                codelets_of_bci = list(
                    map(lambda c: c.codelets[0], linearized_bci))
                bci_comp = Component(
                    codelets_of_bci, i, grammar_name=self.stateless_path, is_tofino=self.is_tofino)
                i += 1
                bci_rooted_at[node.codelets[0].stmt_list[0].lhs] = bci_comp
                for node in linearized_bci:
                    node_to_bci[node].append(bci_comp)
                self.synth_graph.add_node(bci_comp)

        for (u, v) in self.comp_graph.edges:
            print('u: ', str(u))
            print('v: ', str(v))
            for src_comp in node_to_bci[u]:
                for dst_comp in node_to_bci[v]:
                    if src_comp != dst_comp and (src_comp.isStateful or dst_comp.isStateful):
                        self.synth_graph.add_edge(src_comp, dst_comp)

        # Note: synth_graph may contain cycles :-)
        self.draw_graph(self.synth_graph, self.filename + "_synth_graph")

        # Create output processors using synth_graph.
        if self.is_tofino:
            self.synth_output_processor = SketchOutputProcessor(
                self.synth_graph)
        else:
            from domino_postprocessor import DominoOutputProcessor
            self.synth_output_processor = DominoOutputProcessor(
                self.synth_graph)

        # Step 6: Synthesize stateful nodes
        for node in self.synth_graph.nodes:
            if node.isStateful:
                node_name = node.name
                node.set_name(node_name)
                result_file = node.write_sketch_file(
                    self.output_dir, node_name, self.var_types,  stats=self.stats)
                self.synth_output_processor.process_single_stateful_output(
                    result_file, node)

        '''
        # Step 7: Synthesize stateless POs (every output we need to synthesize that is stateless)
        # including a) POs, b) inputs to stateful, c) pkt vars (TODO: need to add c)
        for po in self.principal_outputs:
            bci_comp = bci_rooted_at[po]
            comp_name = bci_comp.name
            result_file = bci_comp.write_sketch_file(
                self.output_dir, comp_name, self.var_types, po, stats=self.stats)
            (bci_comp, comp_name)
            if self.is_tofino and bci_comp.contains_ternary():
                print('processing: output is ternary stateful.')
                for file in result_file:
                    self.synth_output_processor.process_single_stateful_output(
                        file, bci_comp)
            else:
                print("processing: output is stateless.")
                self.synth_output_processor.process_stateless_output(
                    result_file, po)
        '''
        # Step 7: Synthesize stateless POs
        # Synthesize in topological order so that synthesis bound info is available for all inputs
        for comp in nx.topological_sort(self.comp_graph):
            if not comp.isStateful: # stateless
                outputs = comp.codelets[0].get_outputs() # comp should have a single codelet
                assert(len(outputs) == 1)
                o = outputs[0]
                if o in self.principal_outputs:
                    print("---------")
                    print("Synthesizing output ", o)
                    print("---------")
                    bci_comp = bci_rooted_at[o]
                    comp_name = bci_comp.name 
                    result_file, bnd = bci_comp.write_sketch_file(self.output_dir, comp_name, self.var_types, o, self.synth_bounds, stats = self.stats)
                    self.synth_bounds[o] = bnd
                    print("Updated synth bound for {} to {}".format(o, bnd))

                    if self.is_tofino and bci_comp.contains_ternary():
                        print('processing: output is ternary stateful.')
                        self.synth_output_processor.process_single_stateful_output(result_file, bci_comp)
                    else:
                        print("processing: output is stateless.")
                        self.synth_output_processor.process_stateless_output(result_file, o)
            else: # stateful -- update synth_bounds
                assert(comp.isStateful)
                bnd_vars = comp.get_input_bounds(self.synth_bounds)
                input_bnds = list(bnd_vars.keys())
                output = comp.codelet.stateful_output
                if output != None:
                    if len(input_bnds) > 0:
                        self.synth_bounds[output] = max(input_bnds)+1 # stateful ALU can be scheduled only after all inputs are available
                    else:
                        self.synth_bounds[output] = 1 # Can be put in stage 1
                    print("Updated synth bound for {} to {}".format(output, self.synth_bounds[output]))

        # do postprocessing in the postprocessor
        self.synth_output_processor.postprocessing()

        return  # return to constructor

    def process_graph(self):
        self.state_vars = list(set(self.state_vars))
        self.comp_graph = nx.DiGraph()
        self.compute_scc_graph()
        return

    def synthesize_single_comp(self, comp, comp_name):
        if comp.isStateful:
            return comp.write_sketch_file(self.output_dir, comp_name, self.var_types, stats=self.stats)
        else:
            return comp.write_sketch_file(self.output_dir, comp_name, self.var_types, self.principal_outputs, stats=self.stats)

    def do_synthesis(self):
        # Synthesize each codelet
        print("Synthesize each codelet")

        """		for comp in nx.topological_sort(self.comp_graph):
            if comp.isStateful:
                comp.create_used_state_vars(self.comp_graph.successors(comp))

        for comp in nx.topological_sort(self.comp_graph):
            print("-----------------")
            print(" file name: ", self.comp_index[comp],
                  " is_stateful: ", comp.isStateful)
            print(" content: ", str(comp))
            print(" outputs: ", str(comp.outputs))
            print(" state vars (if any):", str(
                comp.state_vars) if comp.isStateful else [])
            print(" used state vars (if any):", str(
                comp.state_vars) if comp.isStateful else [])

        """
        for comp in nx.topological_sort(self.comp_graph):
            print(self.comp_index[comp])
            comp.print()
            print("inputs", comp.inputs)
            print("outputs", comp.outputs)
            comp_name = "comp_{}".format(self.comp_index[comp])
            comp.set_name(comp_name)
            print(" > codelet output directory: " + self.output_dir)
            result_file = self.synthesize_single_comp(comp, comp_name)
            print('result file: ', result_file)
            print("processing sketch output...")
            # TODO: resume processing of outputs. Right now we're just verifying whether
            # the sketch file generated is intact.
            print(" file name: ", result_file,
                  " is_stateful: ", comp.isStateful)
            if comp.isStateful:
                print("processing: output is stateful.")
                self.synth_output_processor.process_single_stateful_output(
                    result_file, comp)

            else:
                if self.is_tofino and comp.contains_ternary():
                    print('processing: output is ternary stateful.')
                    for file in result_file:
                        self.synth_output_processor.process_single_stateful_output(
                            file, comp.outputs[0], comp)
                else:
                    print("processing: output is stateless.")
                    output_idx = 0
                    for file in result_file:
                        self.synth_output_processor.process_stateless_output(
                            file, comp.outputs[output_idx])
                        output_idx += 1
        self.write_comp_graph()
        # nx.draw(self.comp_graph)

    def write_comp_graph(self):
        f_deps = open(os.path.join(self.output_dir, "deps.txt"), 'w+')
        num_nodes = len(self.comp_graph.nodes)
        f_deps.write("{}\n".format(num_nodes))
        for u, v in self.comp_graph.edges:
            f_deps.write("{} {}\n".format(
                self.comp_index[u], self.comp_index[v]))
