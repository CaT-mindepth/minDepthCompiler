from re import A
import os
import ply.lex as lex
import networkx as nx
import copy
from graphviz import Digraph
import subprocess
from sketch_output_processor import SketchOutputProcessor
from dependencyGraph import Codelet

#
# ruijief:
# A custom function for running a Sketch file.
#

def run_sketch(self, sketch_filename, output_file):
		bnd = 0
		while True:
			# run Sketch
			sketch_outfilename =  sketch_filename + ".out"
			print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
			f_sk_out = open(sketch_outfilename, "w+")
			print("running sketch, bnd = {}".format(bnd))
			print("sketch_filename", sketch_filename)
			ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
			print("return code", ret_code)
			if ret_code == 0: # successful
				print("solved")
				result_file = sketch_outfilename
				print("output is in " + result_file)
				return
			else:
				print("failed")
		
			f_sk_out.close()
			bnd += 1

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
	
	# v1 and v2 represent the same variable if the suffixes are numbers
	return v1_suffix.isnumeric() and v2_suffix.isnumeric()

def get_variable_name(v1, v2): # longest common prefix
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
	return var.startswith("p_br_tmp") or var.startswith("pkt_br_tmp")

class Component: # group of codelets
	def __init__(self, codelet_list, id):
		self.codelets = codelet_list # topologically sorted
		self.isStateful = False
		self.grammar_path = "grammars/stateless_tofino.sk"
		self.get_inputs_outputs()
		self.set_component_stmts()
    # Here we name each component using comp_{} 
		self.set_name("comp_" + str(id))

	def set_name(self, name):
		self.name = name

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
		ssa_vars = [o for o in self.outputs if o != var and is_same_var(o, var)]
		if len(ssa_vars) == 0:
			return True # var is the only SSA variable
		var_name = get_variable_name(var, ssa_vars[0])
		ssa_indices = [int(v.replace(var_name, '')) for v in ssa_vars]
		max_index = max(ssa_indices)
		var_index = int(var.replace(var_name, ''))

		return var_index > max_index
			
	def update_outputs(self, adj_comps):
		'''
		Keep output o if
		1. It is used by an adjacent codelet (whether it is a temporary var or not), OR
		2. It is a packet field (SSA var with largest index in this component)
		'''
		redundant_outputs = []
		for o in self.outputs:
			if o not in [i for c in adj_comps for i in c.inputs]: # not used in adjacent component
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

	def merge_components(self, comp):
		print("merge component")
		self.codelet.add_stmts(comp.comp_stmts)
		if not comp.isStateful:
			raise Exception ("Cannot merge a stateful comp, " +  "comp.name, " + "with a stateless comp")
		
        self.set_component_stmts() # update stmts
		self.get_inputs_outputs() # update inputs, outputs
    

	def write_grammar(self, f):
		try:
			f_grammar = open(self.grammar_path)
			# copy gramar
			lines = f_grammar.readlines()
			for l in lines:
				f.write(l)

		except IOError:
			print("Failed to open stateless grammar file {}.".format(self.grammar_path))
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
				if var_types[v] == "int":
					f.write(" {} |".format(v))
		f.write("};\n")
		f.write("\t}\n")

		assert("bit" not in [var_types[v] for v in self.inputs]) # no inputs of type bit

		# f.write("\tgenerator bit bool_vars(){\n")
		# f.write("\t\treturn {| 1 |")
		# # if "bit" in [var_types[v) for v in inputs]:
		# for v in self.inputs:
		# 	if var_types[v] == "bit":
		# 		f.write(" %s |" % v)
		# f.write("};\n")
		# f.write("\t}\n")

		comp_fxn = comp_name + "(" + ", ".join(self.inputs) + ")"

		output_type = var_types[o]
		# TODO: more robust type checking; relational expression can be assigned to an integer variable (should be bool)
		# if output_type == "int":
		assert(output_type == "int")
		f.write("\tassert expr(vars, {}) == {};\n".format(bnd, comp_fxn))
		# else:
		# 	assert(output_type == "bit")
		# 	# f.write("\tassert bool_expr(bool_vars, {}) == {};\n".format(bnd, comp_fxn)
		# 	f.write("\tassert bool_expr(vars, bool_vars, {}) == {};\n".format(bnd, comp_fxn)) # TODO: What if there are int and bool vars?

		f.write("}\n")

	def write_sketch_file(self, output_path, comp_name, var_types):
		i = 0
		for o in self.outputs:
			bnd = 1
			bnd = 0
			while True:
				# run Sketch
				sketch_filename = f"{comp_name}_{i}_bnd_{bnd}.sk"
				sketch_outfilename = sketch_filename + ".out"
				f = open(os.path.join(output_path, sketch_filename), 'w+')
				self.write_grammar(f)
				self.write_sketch_spec(f, var_types, comp_name, o)
				f.write("\n")
				self.write_sketch_harness(f, var_types, comp_name, o, bnd)
				f.close()				
				print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
				f_sk_out = open(sketch_outfilename, "w+")
				print("running sketch, bnd = {}".format(bnd))
				print("sketch_filename", sketch_filename)
				ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
				print("return code", ret_code)
				if ret_code == 0: # successful
					print("solved")
					result_file = sketch_outfilename
					print("output is in " + result_file)
					return
				else:
					print("failed")
		
				f_sk_out.close()
				bnd += 1

	#		max_bnd = 3 # TODO: run till success
	#		while bnd <= max_bnd:
	#			f = open(os.path.join(output_path, f"{comp_name}_{i}_bnd_{bnd}.sk"), 'w+')
	#			self.write_grammar(f)
	#			self.write_sketch_spec(f, var_types, comp_name, o)
	#			f.write("\n")
	#			self.write_sketch_harness(f, var_types, comp_name, o, bnd)
	#			f.close()
	#			bnd += 1
	#		i += 1

	def print(self):
		for s in self.comp_stmts:
			s.print()
	
	def __str__(self):
		return " ".join([s.get_stmt() for s in self.comp_stmts])


class StatefulComponent():
	def __init__(self, stateful_codelet):
		self.codelet = stateful_codelet
		self.salu_inputs = {'metadata_lo': 0, 'metadata_hi': 0, 'register_lo': 0, 'register_hi': 0}
		self.isStateful = True
		self.state_vars = [stateful_codelet.state_var]
		self.state_pkt_fields = [stateful_codelet.get_state_pkt_field()]
		self.comp_stmts = stateful_codelet.get_stmt_list()

		self.grammar_path = "grammars/stateful_tofino.sk"

		self.get_inputs_outputs()

	def set_name(self, name):
		self.name = name

	def get_inputs_outputs(self):
		self.inputs = self.codelet.get_inputs()
		self.outputs = self.codelet.get_outputs()

	def temp_var(self, var):
		if var in self.state_pkt_fields:
			return True
		elif is_branch_var(var):
			return True
		else:
			return False
			
	def last_ssa_var(self, var):
		ssa_vars = [o for o in self.outputs if o != var and is_same_var(o, var)]
		if len(ssa_vars) == 0:
			return True # var is the only SSA variable
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
		TODO: duplicate if there are > 2 outputs
		'''
		redundant_outputs = []
		adj_inputs = [i for c in adj_comps for i in c.inputs]
		print("adj_inputs", adj_inputs)

		for o in self.outputs:
			if o not in self.state_vars:
				if o not in adj_inputs: # not used in adjacent component
					if self.temp_var(o) or (not self.last_ssa_var(o)):
						redundant_outputs.append(o)
						# print("Redundant output: {}".format(o))
				

		print("redundant outputs", redundant_outputs)
		print("state_var", self.state_vars)

		for red_o in redundant_outputs:
			self.outputs.remove(red_o)

		return

	def merge_components(self, comp):
		print("merge component")
		self.codelet.add_stmts(comp.comp_stmts)

		if comp.isStateful:
			if len(self.state_vars) == 2:
				print("Cannot merge stateful component (current component already has 2 state variables)")
				assert(False)
			assert(len(comp.state_vars) == 1)
			self.state_vars.append(comp.state_vars[0])
			self.state_pkt_fields.append(comp.codelet.get_state_pkt_field())
            
		
		self.get_inputs_outputs() # update inputs, outputs
		# state vars are always inputs
		# NOTE: There would be no need to add state vars as inputs explicitly if a codelet could have 2 state vars
		for s_var in self.state_vars:
			if s_var not in self.inputs:
				self.inputs.append(s_var)
		
	def set_alu_inputs(self):
		if len(self.inputs) > 4:
			print("Error: stateful update does not fit in the stateful ALU.")
			exit(1)
		
		for i in self.inputs:
			if i in self.state_vars:
				if self.salu_inputs['register_lo'] == 0:
					self.salu_inputs['register_lo'] = i
				elif self.salu_inputs['register_hi'] == 0:
					self.salu_inputs['register_hi'] = i
				else:
					print("Error: Cannot have > 2 state variables in a stateful ALU.")
					assert(False)
			else:
				if self.salu_inputs['metadata_lo'] == 0:
					self.salu_inputs['metadata_lo'] = i
				elif self.salu_inputs['metadata_hi'] == 0:
					self.salu_inputs['metadata_hi'] = i
				else:
					print("Error: Cannot have > 2 metadata fields in a stateful ALU.")
					assert(False)

		print("salu_inputs", self.salu_inputs)

	def write_grammar(self, f):
		try:
			f_grammar = open(self.grammar_path)
			# copy gramar
			lines = f_grammar.readlines()
			for l in lines:
				f.write(l)

		except IOError:
			print("Failed to open stateful grammar file {}.".format(self.grammar_path))
			exit(1)
		
	def write_sketch_spec(self, f, var_types, comp_name):
		input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
		spec_name = comp_name
		# write function signature
		f.write("int[2] {}({})".format(spec_name, ", ".join(input_types)) + "{\n")
		# declare output array
		output_array = "_out"
		f.write("\tint[2] {};\n".format(output_array))
		# declare defined variables
		defines = self.codelet.get_outputs()
		for v in defines:
			if v not in self.inputs:
				f.write("\t{} {};\n".format(var_types[v], v))
		# function body
		for stmt in self.comp_stmts:
			f.write("\t{}\n".format(stmt.get_stmt()))
		# update output array
		f.write("\t{}[0] = {};\n".format(output_array, self.state_vars[0]))

		assert(len(self.outputs) <= 2) # at most 2 outputs TODO: duplicate component if > 2 outputs
		
		found_output2 = False
		for o in self.outputs:
			if o != self.state_vars[0]:
				found_output2 = True
				f.write("\t{}[1] = {};\n".format(output_array, o))
		
		if not found_output2: # return state var
			f.write("\t{}[1] = {};\n".format(output_array, self.state_vars[0]))

		# return
		f.write("\treturn {};\n".format(output_array))
		f.write("}\n")

	def write_sketch_harness(self, f, var_types, comp_name):
		f.write("harness void sketch(")
		if len(self.inputs) >= 1:
			var_type = var_types[self.inputs[0]]
			f.write("{} {}".format(var_type, self.inputs[0]))

		for v in self.inputs[1:]:
			var_type = var_types[v]
			f.write(", ")
			f.write("{} {}".format(var_type, v))

		f.write(") {\n")

		f.write("\tint[2] impl = salu({}, {}, {}, {});\n".format(
			self.salu_inputs['metadata_lo'], self.salu_inputs['metadata_hi'], self.salu_inputs['register_lo'], self.salu_inputs['register_hi']
		))
		f.write("\tint [2] spec = {}({});\n".format(comp_name, ', '.join(self.inputs)))

		f.write("\tassert(impl[0] == spec[0]);\n")
		f.write("\tassert(impl[1] == spec[1]);\n") 
		f.write("}\n")

	def write_sketch_file(self, output_path, comp_name, var_types):
		i = 0
		for o in self.outputs:
			bnd = 0
			while True:
				# run Sketch
				sketch_filename = os.path.join(output_path, f"{comp_name}_{i}_bnd_{bnd}.sk")
				sketch_outfilename = os.path.join(output_path, f"{comp_name}_{i}_bnd_{bnd}.sk"+ ".out")
				f = open(sketch_filename, 'w+')
				self.set_alu_inputs()
				self.write_grammar(f)
				self.write_sketch_spec(f, var_types, comp_name)
				f.write("\n")
				self.write_sketch_harness(f, var_types, comp_name)
				f.close()
				print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
				f_sk_out = open(sketch_outfilename, "w+")
				print("running sketch, bnd = {}".format(bnd))
				print("sketch_filename", sketch_filename)
				ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
				print("return code", ret_code)
				if ret_code == 0: # successful
					print("solved")
					result_file = sketch_outfilename
					print("output is in " + result_file)
					return
				else:
					print("failed")
		
				f_sk_out.close()
				bnd += 1

	def print(self):
		stmts = self.codelet.get_stmt_list()
		for s in stmts:
			s.print()

	def __str__(self):
		return str(self.codelet)

class Synthesizer:
	def __init__(self, state_vars, var_types, dep_graph, stateful_nodes, filename):
		self.state_vars = state_vars
		self.var_types = var_types
		self.filename = filename
		self.templates_path = "templates"
		self.output_dir = filename

		try:
			os.mkdir(self.output_dir)
		except OSError:
			print("Output directory {} could not be created".format(self.output_dir))
		else:
			print("Created output directory {}".format(self.output_dir))
		
		self.dep_graph = dep_graph # scc_graph in DependencyGraph
		self.stateful_nodes = stateful_nodes
		self.components = []

		# self.stateful_alus = ["raw", "pred_raw", "if_else_raw", "sub", "nested_ifs", "pair"]
		self.stateful_alus = ["raw", "pred_raw", "if_else_raw"]
		print("Synthesizer")
		print("output dir", self.output_dir)
		self.process_graph()
		self.synth_output_processor = SketchOutputProcessor(self.comp_graph)

		# self.synth_output_processor.schedule()

	def get_var_type(self, v):
		if v in self.var_types:
			return self.var_types[v]
		else:
			print("v", v)
			assert("[" in v) # array access
			array_name = v[:v.find("[")]
			assert(array_name in self.var_types)
			return self.var_types[array_name]

	def process_graph(self):
		original_dep_edges = copy.deepcopy(self.dep_graph.edges())
		print("original_dep_edges")
		for u, v in original_dep_edges:
			print("edge")
			print("u")
			u.print()
			print("v")
			v.print()

		print("\n Dep graph nodes")
		for codelet in self.dep_graph.nodes:
			print()
			codelet.print()

		print("\n Dep graph stateful nodes")
		for codelet in self.stateful_nodes:
			print()
			codelet.print()

		self.dep_graph.remove_nodes_from(self.stateful_nodes)
		# remove incoming and outgoing edges
		# self.dep_graph.remove_edges_from([(w, u) for w in self.dep_graph.predecessors(u)])
		# self.dep_graph.remove_edges_from([(u, v) for v in self.dep_graph.successors(u)])

		i = 0
		codelet_component = {} # codelet repr -> component it belongs to
	
		for u in self.stateful_nodes:
			print("stateful codelet ", i)
			stateful_comp = StatefulComponent(u)
			self.components.append(stateful_comp)
			codelet_component[str(u)] = stateful_comp
			# output_file = "{}_stateful_{}".format(self.filename, i)
			# codelet_name = "stateful_{}".format(i)
			# self.synthesize_stateful_codelet(u, codelet_name, output_file) # TODO: synthesize stateful components
			# self.synthesize_stateful_codelet_tofino(u, codelet_name, output_file) # TODO: synthesize stateful components
			i += 1
	
		i = 0
		for comp in nx.weakly_connected_components(self.dep_graph):
			print("component ", i)
			# print("".join([s.get_stmt() for v in comp for s in v.get_stmt_list()]))
			comp_sorted = []
			for codelet in nx.topological_sort(self.dep_graph):
				if codelet in comp:
					comp_sorted.append(codelet)

			component = Component(comp_sorted, i)

			for codelet in comp_sorted:
				codelet_component[str(codelet)] = component

			self.components.append(component)

			# output_file = "{}_comp_{}".format(self.filename, i)
			# self.synthesize_comp(component, output_file, i) # synthesize component
			i += 1

		####
		print("\n Original_dep_edges")
		for u, v in original_dep_edges:
			print("edge")
			print("u")
			u.print()
			print("v")
			v.print()
		print()
		######

		print("codelet_component", codelet_component)

		# create component graph
		print("Add component graph edges")
		self.comp_graph = nx.DiGraph()
		self.comp_graph.add_nodes_from(self.components)	
		for u, v in original_dep_edges: # add edges between components
			if codelet_component[str(u)] != codelet_component[str(v)]:
				self.comp_graph.add_edge(codelet_component[str(u)], codelet_component[str(v)])
				print(str(codelet_component[str(u)]))
				print("->")
				print(str(codelet_component[str(v)]))
				print()

		# Duplicate components to eliminate inputs of type bit (branch variables)
		outputs_comp = {} # output -> component

		for comp in nx.topological_sort(self.comp_graph):
			for input in comp.inputs:
				if self.var_types[input] == 'bit':
					print("Found input of type bit")
					print("Copy preceding component")
					prec_comp = outputs_comp[input]
					if prec_comp.isStateful:
						# new_codelet = Codelet(prec_comp.codelet.get_stmt_list())
						# # TODO: restructure Codelet class so that this initialization is not needed
						# new_codelet.stateful = True # it is a stateful codelet
						# new_codelet.state_var = prec_comp.codelet.state_var
						# #########
						
						new_comp = copy.deepcopy(prec_comp)
						new_comp.merge_components(comp)
						self.comp_graph.add_node(new_comp)
						self.comp_graph.add_edges_from([(x, new_comp) for x in 
							self.comp_graph.predecessors(prec_comp)])
						self.comp_graph.add_edges_from([(new_comp, y) for 
							y in self.comp_graph.successors(comp)])
						
						if comp.isStateful:
							comp.codelet.state_var

						# Delete prec_comp (new_comp subsumes it)
						self.comp_graph.remove_node(prec_comp)
						# NOTE: If merged component doesn't fit, throw an error
						# TODO: Handle this case, maybe by splitting the merged component
					else:
						print("TODO: Not implemented yet")
						assert(False)
					
					self.comp_graph.remove_node(comp)
					comp = new_comp

			comp.update_outputs(self.comp_graph.neighbors(comp))
			comp.print()
			print("inputs", comp.inputs)
			print("outputs", comp.outputs)

			# update outputs_comp map
			for o in comp.outputs:
				outputs_comp[o] = comp

			# if comp.isStateful:
			# 	self.synthesize_stateful_tofino(comp, comp_name)
			# else:
			# 	self.synthesize_stateless_tofino(comp, comp_name)

		self.comp_index = {} # component -> index
		print("comp index", self.comp_index)
		# check for redundant outputs
		print("Eliminate redundant outputs after merging")
		i = 0
		for comp in nx.topological_sort(self.comp_graph):
			self.comp_index[comp] = i
			print(i)
			comp.print()
			comp.update_outputs(self.comp_graph.neighbors(comp))
			print("inputs", comp.inputs)
			print("outputs", comp.outputs)
			i += 1

		# Synthesize each codelet
		print("Synthesize each codelet")
		for comp in nx.topological_sort(self.comp_graph):
			print(self.comp_index[comp])
			comp.print()
			print("inputs", comp.inputs)
			print("outputs", comp.outputs)
			comp_name = "comp_{}".format(self.comp_index[comp])
			comp.set_name(comp_name)
			print(" > codelet output directory: " + self.output_dir)
			comp.write_sketch_file(self.output_dir, comp_name, self.var_types)


		self.write_comp_graph()
		# nx.draw(self.comp_graph)

	def write_comp_graph(self):
		f_deps = open(os.path.join(self.output_dir, "deps.txt"), 'w+')
		num_nodes = len(self.comp_graph.nodes)
		f_deps.write("{}\n".format(num_nodes))
		for u, v in self.comp_graph.edges:
			f_deps.write("{} {}\n".format(self.comp_index[u], self.comp_index[v]))

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
	
			sketch_outfilename =  sketch_filename + ".out"
			print("sketch {} > {}".format(sketch_filename, sketch_outfilename))

			f_sk_out = open(sketch_outfilename, "w+")

			print("running sketch, alu {}".format(alu))
			print("sketch_filename", sketch_filename)
			ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
			print("return code", ret_code)
			if ret_code == 0: # successful
				print("solved")
				result_file = sketch_outfilename
				print("output is in " + result_file)
				# self.synth_output_processor.process_stateful_output(result_file, o)
				break
			else:
				print("Stateful codelet does not fit in {} ALU".format(alu))
		
			
			f_sk_out.close()


	def synthesize_comp(self, component, output_file, comp_index):
		other_inputs = [i for comp in self.components for i in comp.inputs] + [i for s in self.stateful_nodes for i in s.get_inputs()]
		used_outputs = [o for o in component.outputs if o in other_inputs] # outputs of component that are inputs of other components
		if len(used_outputs) == 0: # TODO: packet variable is always an output
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
			sketch_outfilename =  sketch_filename + ".out"
			print("sketch {} > {}".format(sketch_filename, sketch_outfilename))

			f_sk_out = open(sketch_outfilename, "w+")

			print("running sketch, bnd = {}".format(bnd))
			print("sketch_filename", sketch_filename)
			ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
			print("return code", ret_code)
			if ret_code == 0: # successful
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
		f.write("{} {}({})".format(self.get_var_type(output), fxn_name, ", ".join(input_types)) +  "{\n")
		# declare outputs
		for o in outputs:
			if o not in inputs:
				f.write("\t{} {};\n".format(self.get_var_type(o), o))

		for stmt in stmts:
			f.write("\t{}\n".format(stmt.get_stmt()))
			print("\t{}\n".format(stmt.get_stmt()))

		f.write("\treturn {};\n".format(output))
		f.write("}\n")

	def write_harness_bnd(self, f, comp_fxn_name, inputs, output, bnd ):
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
			assert(output_type == "bit")
			# f.write("\tassert bool_expr(bool_vars, {}) == {};\n".format(bnd, comp_fxn)
			f.write("\tassert bool_expr(vars, bool_vars, {}) == {};\n".format(bnd, comp_fxn)) # TODO: What if there are int and bool vars?

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
			return 2 # no. of arguments
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
			assert(False)


	def write_raw_alu(self, f, inputs, output):
		if len(inputs) > 1:
			print("Too many inputs")
			return False
		else:
			pkt_0 = inputs[0]
			state_var = output
			assert(state_var in self.state_vars)

			f.write("{} raw({}, {})".format(self.get_var_type[state_var], "{} {}".format(self.get_var_type[state_var], state_var), 
			"{} {}".format(self.get_var_type[pkt_0], pkt_0)))

			f.write("{} = Opt({}) + Mux2({}, C())".format(state_var, state_var, pkt_0))
			f.write("return {}".format(state_var))


	def write_stateless_grammar(self, f):
		
		f_template = open(self.templates_path + "/stateless_grammar.sk", "r")
		# f_template = open(self.templates_path + "/stateless_tofino.sk", "r")
		self.copy(f_template, f)
		f_template.close()