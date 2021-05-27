import sys
import ply.lex as lex
import lexerRules
import networkx as nx
from graphviz import Digraph
import subprocess
from sketch_output_processor import SketchOutputProcessor


class Component:  # group of codelets
  def __init__(self, codelet_list):
    self.codelets = codelet_list  # topologically sorted
    self.get_inputs_outputs()
    self.get_component_stmts()

  def get_inputs_outputs(self):
    self.inputs = []
    outputs = set()
    for codelet in self.codelets:
      ins = codelet.get_inputs()
      outs = codelet.get_outputs()
      self.inputs.extend([i for i in ins if (i not in outputs) and (i not in self.inputs)])
      outputs.update(outs)

    self.outputs = list(outputs)

    for input1 in self.inputs:
      for input2 in self.inputs:
        if input1 == input2:
          print("HAHAHAHAHA found it, input is " + input1)
          exit(10)

  def get_component_stmts(self):
    self.comp_stmts = []
    for codelet in self.codelets:
      self.comp_stmts.extend(codelet.get_stmt_list())


class Synthesizer:
  def __init__(self, state_vars, var_types, dep_graph, stateful_nodes, filename):
    self.state_vars = state_vars
    self.var_types = var_types
    self.filename = filename
    self.templates_path = "templates"

    self.dep_graph = dep_graph
    self.stateful_nodes = stateful_nodes
    self.components = []

    # self.stateful_alus = ["raw", "pred_raw", "if_else_raw", "sub", "nested_ifs", "pair"]
    self.stateful_alus = ["raw", "pred_raw", "if_else_raw"]

    self.synth_output_processor = SketchOutputProcessor()
    print("Synthesizer")
    print("stateful nodes", self.stateful_nodes)
    self.process_graph()
    self.synth_output_processor.schedule()

  def get_var_type(self, v):
    if v in self.var_types:
      return self.var_types[v]
    else:
      print("v", v)
      assert ("[" in v)  # array access
      array_name = v[:v.find("[")]
      assert (array_name in self.var_types)
      return self.var_types[array_name]

  def process_graph(self):

    self.dep_graph.remove_nodes_from(self.stateful_nodes)
    # remove incoming and outgoing edges
    # self.dep_graph.remove_edges_from([(w, u) for w in self.dep_graph.predecessors(u)])
    # self.dep_graph.remove_edges_from([(u, v) for v in self.dep_graph.successors(u)])

    i = 0;
    print("---------- processing stateful codelets -----------------------------")
    for u in self.stateful_nodes:
      print("stateful codelet ", i)
      output_file = "{}_stateful_{}".format(self.filename, i)
      codelet_name = "stateful_{}".format(i)
      self.synthesize_stateful_codelet(u, codelet_name, output_file)  # TODO: synthesize stateful components
      i += 1

    i = 0;
    print("--------- processing weach weakly connected components --------------")
    for comp in nx.weakly_connected_components(self.dep_graph):
      print("component ", i)
      # print("".join([s.get_stmt() for v in comp for s in v.get_stmt_list()]))
      comp_sorted = []
      for codelet in nx.topological_sort(self.dep_graph):
        if codelet in comp:
          comp_sorted.append(codelet)

      component = Component(comp_sorted)
      self.components.append(component)

      output_file = "{}_comp_{}".format(self.filename, i)
      self.synthesize_comp(component, output_file, i)  # synthesize component
      i += 1

  def synthesize_stateful_codelet(self, codelet, codelet_name, output_file):
    inputs = codelet.get_inputs()
    outputs = codelet.get_outputs()
    o = codelet.get_state_pkt_field()
    print("inputs", inputs)
    print("outputs", outputs)
    print("o", o)

    stmts = codelet.get_stmt_list()

    for alu in self.stateful_alus:
      sketch_filename = "{}_{}_{}.sk".format(output_file, o, alu)
      f = open(sketch_filename, "w+")
      self.write_stateful_generators(f)
      num_args = self.write_stateful_alu(f, codelet_name, inputs, o, alu)
      if len(inputs) > num_args:
        print("Too many inputs, skipping this alu")
        continue
      self.write_fxn(f, codelet_name, inputs, outputs, o, stmts, num_args)
      f.close()

      sketch_outfilename = sketch_filename + ".out"
      print("sketch {} > {}".format(sketch_filename, sketch_outfilename))

      f_sk_out = open(sketch_outfilename, "w+")

      print("running sketch, alu {}".format(alu))
      print("sketch_filename", sketch_filename)
      ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
      print("return code", ret_code)
      if ret_code == 0:  # successful
        print("solved")
        result_file = sketch_outfilename
        print("output is in " + result_file)
        # self.synth_output_processor.process_stateful_output(result_file, o)
        break
      else:
        print("Stateful codelet does not fit in {} ALU".format(alu))

      f_sk_out.close()

  def synthesize_comp(self, component, output_file, comp_index):
    other_inputs = [i for comp in self.components for i in comp.inputs] + [i for s in self.stateful_nodes for i in
                                                                           s.get_inputs()]
    used_outputs = [o for o in component.outputs if
                    o in other_inputs]  # outputs of component that are inputs of other components
    if len(used_outputs) == 0:  # TODO: packet variable is always an output
      used_outputs = component.outputs
    print("used_outputs", used_outputs)

    for o in used_outputs:
      component_name = "comp_{}".format(comp_index)
      self.run_sketch(component.inputs, component.outputs, o, component.comp_stmts, component_name, output_file)

  def run_sketch(self, inputs, outputs, output, comp_stmts, component_name, output_file):
    bnd = 0
    while True:
      sketch_filename = "{}_out_{}_bnd_{}.sk".format(output_file, output, bnd)
      f = open(sketch_filename, "w+")
      self.write_stateless_grammar(f)
      self.write_fxn(f, component_name, inputs, outputs, output, comp_stmts, len(inputs))
      self.write_harness_bnd(f, component_name, inputs, output, bnd)
      f.close()
      # run Sketch
      sketch_outfilename = sketch_filename + ".out"
      print("sketch {} > {}".format(sketch_filename, sketch_outfilename))

      f_sk_out = open(sketch_outfilename, "w+")

      print("running sketch, bnd = {}".format(bnd))
      print("sketch_filename", sketch_filename)
      ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
      print("return code", ret_code)
      if ret_code == 0:  # successful
        print("solved")
        result_file = sketch_outfilename
        print("output is in " + result_file)
        self.synth_output_processor.process_output(result_file, output)
        break
      else:
        print("failed")

      f_sk_out.close()
      bnd += 1

  def write_fxn(self, f, fxn_name, inputs, outputs, output, stmts, num_args):
    print("inputs", inputs)
    input_types = ["{} {}".format(self.get_var_type(i), i) for i in inputs]

    i = 0
    extra_inputs = []
    if len(inputs) < num_args:
      for i in range(num_args - len(inputs)):
        extra_inputs.append("_temp{}".format(i))
        input_types.append("int _temp{}".format(i))

    print("input_types", input_types)
    print("output", output)
    f.write("{} {}({})".format(self.get_var_type(output), fxn_name, ", ".join(input_types)) + "{\n")
    # declare outputs
    for o in outputs:
      if o not in inputs:
        f.write("\t{} {};\n".format(self.get_var_type(o), o))

    for stmt in stmts:
      f.write("\t{}\n".format(stmt.get_stmt()))
      print("\t{}\n".format(stmt.get_stmt()))

    f.write("\treturn {};\n".format(output))
    f.write("}\n")

  def write_harness_bnd(self, f, comp_fxn_name, inputs, output, bnd):
    f.write("harness void sketch(")
    if len(inputs) >= 1:
      var_type = self.get_var_type(inputs[0])
      f.write("%s %s" % (var_type, inputs[0]))

    for v in inputs[1:]:
      var_type = self.get_var_type(v)
      f.write(", ")
      f.write("%s %s" % (var_type, v))

    f.write(") {\n")

    print("var_types values", self.var_types.values())
    f.write("\tgenerator int vars(){\n")
    f.write("\t\treturn {| 1 |")
    if "int" in [self.get_var_type(v) for v in inputs]:
      # f.write("|");
      for v in inputs:
        if self.get_var_type(v) == "int":
          f.write(" %s |" % v)
    f.write("};\n")
    f.write("\t}\n")

    f.write("\tgenerator bit bool_vars(){\n")
    f.write("\t\treturn {| 1 |")
    # if "bit" in [self.get_var_type(v) for v in inputs]:
    for v in inputs:
      if self.get_var_type(v) == "bit":
        f.write(" %s |" % v)
    f.write("};\n")
    f.write("\t}\n")

    comp_fxn = comp_fxn_name + "(" + ", ".join(inputs) + ")"

    output_type = self.get_var_type(output)
    # TODO: more robust type checking; relational expression can be assigned to an integer variable (should be bool)
    if output_type == "int":
      f.write("\tassert expr(vars, bool_vars, {}) == {};\n".format(bnd, comp_fxn))
    else:
      assert (output_type == "bit")
      # f.write("\tassert bool_expr(bool_vars, {}) == {};\n".format(bnd, comp_fxn)
      f.write("\tassert bool_expr(vars, bool_vars, {}) == {};\n".format(bnd,
                                                                        comp_fxn))  # TODO: What if there are int and bool vars?

    f.write("}\n")

  def copy_stateful(self, f_read, f, codelet_name):
    lines = f_read.readlines()
    for i in range(len(lines)):
      if i == 0:
        f.write(lines[i].format(codelet_name))
      else:
        f.write(lines[i])

    f.write("\n")

  def copy(self, f_read, f):
    for l in f_read.readlines():
      f.write(l)

    f.write("\n")

  def write_stateful_generators(self, f):
    f_rel = open(self.templates_path + "/rel_ops.sk", "r")
    self.copy(f_rel, f)
    f_rel.close()

    f_mux = open(self.templates_path + "/muxes.sk", "r")
    self.copy(f_mux, f)
    f_mux.close()

    f_const = open(self.templates_path + "/constants.sk", "r")
    self.copy(f_const, f)
    f_const.close()

    f_arith = open(self.templates_path + "/arith_ops.sk", "r")
    self.copy(f_arith, f)
    f_arith.close()

  def write_stateful_alu(self, f, codelet_name, inputs, output, alu_name):
    if alu_name == "raw":
      f_raw = open(self.templates_path + "/raw.sk", "r")
      self.copy_stateful(f_raw, f, codelet_name)
      # self.write_raw_alu(f, inputs, output, codelet_name)
      f_raw.close()
      return 2  # no. of arguments
    elif alu_name == "pred_raw":
      f_pred_raw = open(self.templates_path + "/pred_raw.sk", "r")
      self.copy_stateful(f_pred_raw, f, codelet_name)
      f_pred_raw.close()
      return 3
    elif alu_name == "if_else_raw":
      f_if_else_raw = open(self.templates_path + "/if_else_raw.sk", "r")
      self.copy_stateful(f_if_else_raw, f, codelet_name)
      f_if_else_raw.close()
      return 3
    elif alu_name == "sub":
      f_sub = open(self.templates_path + "/sub.sk", "r")
      self.copy_stateful(f_sub, f, codelet_name)
      f_sub.close()
    # TODO: return number of arguments
    elif alu_name == "nested_ifs":
      f_nested_ifs = open(self.templates_path + "/nested_ifs.sk", "r")
      self.copy_stateful(f_nested_ifs, f, codelet_name)
      f_nested_ifs.close()
    # TODO: return number of arguments
    elif alu_name == "pair":
      f_pair = open(self.templates_path + "/pair.sk", "r")
      self.copy_stateful(f_pair, f, codelet_name)
      f_pair.close()
    # TODO: return number of arguments
    else:
      print("Error: unknown ALU")
      assert (False)

  def write_raw_alu(self, f, inputs, output):
    if len(inputs) > 1:
      print("Too many inputs")
      return False
    else:
      pkt_0 = inputs[0]
      state_var = output
      assert (state_var in self.state_vars)

      f.write(
        "{} raw({}, {})".format(self.get_var_type[state_var], "{} {}".format(self.get_var_type[state_var], state_var),
                                "{} {}".format(self.get_var_type[pkt_0], pkt_0)))

      f.write("{} = Opt({}) + Mux2({}, C())".format(state_var, state_var, pkt_0))
      f.write("return {}".format(state_var))

  def write_stateless_grammar(self, f):

    f_template = open(self.templates_path + "/stateless_grammar.sk", "r")
    # f_template = open(self.templates_path + "/stateless_tofino.sk", "r")
    self.copy(f_template, f)
    f_template.close()
