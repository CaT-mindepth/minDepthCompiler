from re import A
import os
import ply.lex as lex
import networkx as nx
import copy
from graphviz import Digraph
import subprocess
from sketch_output_processor import SketchOutputProcessor
from dependencyGraph import Codelet
from dependencyGraph import Statement

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

	# This merge_component should be removed since two stateless components cannot be merged
	def merge_component(self, comp):
		print("merge component")
		self.codelet.add_stmts(comp.comp_stmts)
		if comp.isStateful:
			raise Exception ("Cannot merge a stateful comp, " +  "comp.name, " + "with a stateless comp")
		else:
			self.set_component_stmts()
			self.get_inputs_outputs()
		
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
#ruijief: TODO TODO

		if not ("bit" not in [var_types[v] for v in self.inputs]): # no inputs of type bit
			print('ERROR: bit present in inputs')
			assert False
		#f.write("\tgenerator bit bool_vars(){\n")
		#f.write("\t\treturn {| 1 |")
		#if "bit" in [var_types[v] for v in self.inputs]:
	#		for v in self.inputs:
#		 		if var_types[v] == "bit":
#		 			f.write(" %s |" % v)
#			f.write("};\n")
#			f.write("\t}\n")

		comp_fxn = comp_name + "(" + ", ".join(self.inputs) + ")"

		output_type = var_types[o]
		# TODO: more robust type checking; relational expression can be assigned to an integer variable (should be bool)
		# if output_type == "int":
		# print(' - TODO output type of ', o, ' is int? but it is ', output_type)
		if not (output_type == "int"):
			print('ERROR:bit present as output type')
			assert False
		f.write("\tassert expr(vars, {}) == {};\n".format(bnd, comp_fxn))
		# else:
		# 	assert(output_type == "bit")
		# 	# f.write("\tassert bool_expr(bool_vars, {}) == {};\n".format(bnd, comp_fxn)
		# 	f.write("\tassert bool_expr(vars, bool_vars, {}) == {};\n".format(bnd, comp_fxn)) # TODO: What if there are int and bool vars?

		f.write("}\n")

	def write_sketch_file(self, output_path, comp_name, var_types):
		filenames = []
		for o in self.outputs:
			bnd = 1 # start with bound 1, since ALU cannot be a wire (which is bnd 0)
			while True:
				# run Sketch
				sketch_filename = os.path.join(output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk")
				sketch_outfilename = os.path.join(output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk.out")
				f = open(sketch_filename, 'w+')
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
					filenames.append(result_file)
					break
				else:
					print("failed")
		
				f_sk_out.close()
				bnd += 1
		return filenames
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

class StatefulComponent(object):
	def __init__(self, stateful_codelet):
		self.codelet = stateful_codelet
		self.salu_inputs = {'metadata_lo': 0, 'metadata_hi': 0, 'register_lo': 0, 'register_hi': 0}
		self.isStateful = True
		self.state_vars = [stateful_codelet.state_var]
		self.state_pkt_fields = stateful_codelet.get_state_pkt_field()
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

	def merge_component(self, comp, reversed=False):
		print("merge component: component is ---- ", self)
		print(' ********************** adding statements from component ', comp, ' with *************************')
		print(comp.comp_stmts)
		if reversed:
			self.codelet.add_stmts_before(comp.comp_stmts)
		else:
			self.codelet.add_stmts(comp.comp_stmts)

		if comp.isStateful:
			if len(self.state_vars) == 2:
				print("Cannot merge stateful component (current component already has 2 state variables)")
				assert(False)
			assert(len(comp.state_vars) == 1)
			self.state_vars.append(comp.state_vars[0])
			self.state_pkt_fields += (comp.codelet.get_state_pkt_field()) # get_state_pkt_field() returns a list
		
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
		
		print("~~~~~~~~~~set_alu_inputs: ", self.inputs)
		print(" ~~~| state var: ", self.state_vars)
		self.salu_inputs['register_lo'] = 0
		self.salu_inputs['register_hi'] = 0
		self.salu_inputs['metadata_lo'] = 0
		self.salu_inputs['metadata_hi'] = 0
		for i in self.inputs:
			if i in self.state_vars:
				if self.salu_inputs['register_lo'] == 0:
					self.salu_inputs['register_lo'] = i
				elif self.salu_inputs['register_hi'] == 0:
					self.salu_inputs['register_hi'] = i
				else:
					print("Error: Cannot have > 2 state variables in a stateful ALU. Component: ", str(self))
					print(' problematic inputs: ', self.inputs)
					print(' problematic state vars: ', self.state_vars)
					assert(False)
			else:
				if self.salu_inputs['metadata_lo'] == 0:
					self.salu_inputs['metadata_lo'] = i
				elif self.salu_inputs['metadata_hi'] == 0:
					self.salu_inputs['metadata_hi'] = i
				else:
					print("Error: Cannot have > 2 metadata fields in a stateful ALU. Component: ", str(self))
					print(' problematic inputs: ', self.inputs)
					print(' problematic state vars: ', self.state_vars)
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

		if not(len(self.outputs) <= 2): # at most 2 outputs TODO: duplicate component if > 2 outputs
			print('ERROR: outputs are ', self.outputs, ' which is more than 2.')
			assert False
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

	def write_sketch_file(self, output_path, comp_name, var_types, upper_bnd = 2, prefix=""): # TODO: remove bounds from stateful synthesis
		bnd = 1 # start with bound 1, since SALU cannot be a wire (which is bnd 0)
		while True:
			# run Sketch
			# if optionally, upper_bnd is specified, then 
			# we check if bound exceeds upper bound, and perform synthesis
			if upper_bnd != -1 and bnd >= upper_bnd: 
				return None
			
			sketch_filename = os.path.join(output_path, prefix + f"{comp_name}_stateful_bnd_{bnd}.sk")
			sketch_outfilename = os.path.join(output_path, prefix + f"{comp_name}_stateful_bnd_{bnd}.sk"+ ".out")
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
				return result_file 
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
	def __init__(self, state_vars, var_types, dep_graph, stateful_nodes, filename, p4_output_name):
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

		print("Synthesizer")
		print("output dir", self.output_dir)
		self.process_graph()
		self.synth_output_processor = SketchOutputProcessor(self.comp_graph)
		self.do_synthesis()
		self.synth_output_processor.postprocessing()
		print(self.synth_output_processor.to_ILP_str(table_name="NewTable"))


	def get_var_type(self, v):
		if v in self.var_types:
			return self.var_types[v]
		else:
			print("v", v)
			assert("[" in v) # array access
			array_name = v[:v.find("[")]
			assert(array_name in self.var_types)
			return self.var_types[array_name]

	# returns True iff merging a, b increases depth of DAG by 1.
	# this is a symmetric condition.
	def merging_increases_depth(self, a, b):
		# import graphutil 
		# return (graphutil.merge_increases_depth(a, b))
		return False # XXX: Since we implement predecessor packing check, we skip this for now.
	
	# calls sketch to determine if component A+B is synthesizeable.
	def try_merge(self, a, b, k=3):
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
		print('resultant component: ')
		print(new_comp)
		print('new component inputs: ', new_comp.inputs)
		print('new component outputs: ', new_comp.outputs)
		print('new component state_pkt_fields: ', new_comp.state_pkt_fields)

		new_comp.update_outputs(self.comp_graph.neighbors(b))
		print('-------------- Merging... -------------')
		try:
			result = new_comp.write_sketch_file(self.output_dir, new_comp.name, self.var_types,\
				upper_bnd=k, prefix='try_merge_')
			if result == None:
				print('---------- Merge failure. ---------')
				return False
			else:
				print('---------- Merge success. ---------')
				return True
		except: 
			print('AssertionError? failed ')
			print('---------- Merge failure. ---------')
			return False
	# def all_phv_outputs(self):
	#	# PHV outputs are outputs that aren't branch variables (e.g. branch variables are of type bit)
	#	# and not state variables
	#	return list(filter(lambda x: not (x in self.state_vars) and not (self.var_types[x] == 'bit'), self.outputs))

	def non_temporary_outputs(self, comp):
		x= list(filter(lambda x: not self.var_types[x] == 'bit', comp.outputs))
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
			filtered_outputs = list(filter(lambda x: not self.var_types[x] == 'bit', filtered_outputs))
			print(' exclude_read_write_flanks: filtered outputs (temp filtered): ', filtered_outputs)
		else:
			print(' exclude_read_write_flanks: filtered outputs (temp unfiltered): ', filtered_outputs)

		return filtered_outputs 

	def merge_candidate(self, a, b):
		a.update_outputs(self.comp_graph.neighbors(a))
		b.update_outputs(self.comp_graph.neighbors(b))
		print(' ~ merge_candidate: a inputs : ', a.inputs)
		print(' ~ merge_candidate: a outputs : ', a.outputs)
		print(' ~ merge_candidate: b inputs : ', b.inputs)
		print(' ~ merge_candidate: b outputs : ', b.outputs)
		# PRECONDITION: a has to be predecesssor of b, 
		# i.e. a-->b is an edge.
		# returns True if components A and B are valid merge candidates.

		# Two components are stateless. Return false.
		if not (a.isStateful or b.isStateful): # if a and b are both stateless, return
			print('    ~ merge_candidate: both components are stateless.')
			return False
		
		# Check for predecessor packing condition.		
		if len(list(self.comp_graph.successors(a))) != 1:
			print('    ~ merge_candidate: predecessor packing condition not met.')
			return False 
		else:
			assert list(self.comp_graph.successors(a))[0] == b

		#
		# check outputs 
		#

		if a.isStateful: 
			if len(a.state_vars) != 1:
				print('		~ merge_candidate: component a state_vars length != 1')
		if b.isStateful:
			if len(b.state_vars) != 1:
				print('		~ merge_candidate: component b state_vars length != 1')
		
		merged_output_vars = set(a.outputs) # self.exclude_read_write_flanks(a, filter_temporaries=False)
		merged_output_vars.update(b.outputs) # self.exclude_read_write_flanks(b, filter_temporaries=False)
		# now merged_output_vars contains both a and b's outputs, deduplicated. 
		# vars needed post-merge. Since succ(a) = {b}, only vars needed are b's out-neighbors' inputs.
		b_succ_inputs = set()
		for b_succ in self.comp_graph.successors(b):
			b_succ_inputs.update(b_succ.inputs) 
		
		merged_output_vars = list(merged_output_vars.intersection(b_succ_inputs))
		print('		| merge_candidate: a_output_vars : ', a.outputs)
		print('		| merge_candidate: b_output_vars : ', b.outputs)
		print('		| merge_candidate: merged output_vars : ', merged_output_vars)
		
		if len(merged_output_vars) > 2:
			print('		~ merge_candidate: cannot merge a and b because too many output variables.')
		#
		#  check inputs size
		#
		print('     ~ merge_candidate: checking inputs size...')
		print('     | a inputs: ', a.inputs)
		print('     | b inputs: ', b.inputs)
		# since a-->b, we filter inputs to b that are a's outputs. 
		merged_inputs = set(a.inputs)
		merged_inputs.update(b.inputs)
		merged_inputs = list(merged_inputs)
		merged_inputs = list(filter(lambda x: x not in a.outputs, merged_inputs))
		print('     | merged inputs: ', merged_inputs)

		merged_state_vars = set()
		if a.isStateful:
			merged_state_vars.update(a.state_vars)
		if b.isStateful:
			merged_state_vars.update(b.state_vars)
		merged_stateless_vars = list(filter(lambda x: x not in merged_state_vars, merged_inputs))
		print('		| merged state vars: ', merged_state_vars)
		print('		| merged stateless vars: ', merged_stateless_vars)
		if len(merged_state_vars) > 2 or len(merged_stateless_vars) > 2:
			print(' 	| cannot merge: too many inputs.')
			return False
		else: 
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
		else: # b must be a stateful comp
			new_comp = copy.deepcopy(b)
			new_comp.merge_component(a, True)

		# create new merged component, add edges
		self.comp_graph.add_node(new_comp)
		self.comp_graph.add_edges_from([(x, new_comp) for x in self.comp_graph.predecessors(a)])
		self.comp_graph.add_edges_from([(new_comp, y) for y in self.comp_graph.successors(b)])
		# remove two old components
		self.comp_graph.remove_node(a)
		self.comp_graph.remove_node(b)
		new_comp.update_outputs(self.comp_graph.neighbors(new_comp))
		print('		* new component : ', new_comp)
		print('		* new component inputs : ', new_comp.inputs)
		print('		* new component outputs : ', new_comp.outputs)
		print('		* state_pkt_fields of new component: ', new_comp.state_pkt_fields)
		return new_comp

	def reverse_top_order(self):
		top = list(nx.topological_sort(self.comp_graph))
		top.reverse() 
		return top 

	def recursive_merge(self):
		nodes = self.reverse_top_order() 
		print(' * recursive_merge strategy: nodes ordered ', list(map(lambda x: str(x), nodes)))
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
					if self.merge_candidate(pred, node):
						# try calling sketch to synthesize new component. 
						if self.try_merge(pred, node):
							# merging successful. 
							self.merge_processed.add(pred)
							self.merge_processed.add(node)
							merged_component = self.perform_merge(pred, node)
							self.recursive_merge() 
							halt = True 
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

	def transfer_branch_vars(self):
		#for comp in nx.topological_sort(self.comp_graph):
		comps = list(nx.topological_sort(self.comp_graph))
		comp_transform = {}
		for comp in comps:
			comp_transform[comp] = comp
		modified_lhses = []

		print('transfer_branch_vars: finding stateless branch variables to move to int...')
		for comp_old in comps:
			comp = comp_transform[comp_old]
			if not comp.isStateful:
				# is stateless component.
				# XXX: quick check if the current component is a branch tmp var component of one.
				if len(comp.outputs) == 1 and self.var_types[comp.outputs[0]] == 'bit' \
					and 'tmp' in comp.outputs[0]:
					print(' * transfer_branch_vars: found a stateless component to doctor: ', str(comp))
					assert len(comp.codelets) == 1
					assert len(comp.codelets[0].stmt_list) == 1
					# change its type to int
					self.var_types[comp.outputs[0]] = 'int'
					stmt = comp.codelets[0].stmt_list[0]
					print('    | statement: ', str(stmt))
					# (self, lhs, rhs, line_no)
					#	dependencyGraph.Statement(lhs, rhs, line_no)
					modified_lhses.append(stmt.lhs)
					new_stmt = Statement(stmt.lhs, '( ' + stmt.rhs + ") ? 1 : 0", stmt.line_no)
					# new stmt init 
					new_stmt.find_rhs_vars()
					new_stmt.is_read_flank(self.state_vars)
					new_stmt.is_write_flank(self.state_vars)

					print('    | new statement: ', str(new_stmt))

					new_codelet = Codelet([new_stmt]) 
					assert new_codelet.is_stateful(self.state_vars) != False
					new_comp = StatefulComponent(new_codelet)
					
					print('    | new component: ', str(new_comp))

					# add in new_comp and delete current component.
					comp_transform[comp] = new_comp
					self.comp_graph.add_node(comp)
					self.comp_graph.add_edges_from([(new_comp, succ) for succ in self.comp_graph.successors(comp)])
					self.comp_graph.add_edges_from([(pred, new_comp) for pred in self.comp_graph.predecessors(comp)])
					self.comp_graph.remove_node(comp)
					new_comp.get_inputs_outputs()
		print(' ***** transfer_branch_vars: finished creating new components. Now finding RHSes.')
		comps = list(nx.topological_sort(self.comp_graph))
		for comp in comps:
			lexer = lex.lex(module=lexerRules)
			def modify_stmt(stmt, lexer, branch_var):
				rhs = stmt.rhs 
				old_rhs = rhs
				rhs = rhs.replace(branch_var, '(' + branch_var + '==1)')
				stmt.rhs = rhs 
				print('         - modify_stmt: previous rhs ', old_rhs, '; current rhs ', rhs)
				return stmt
			print(' | looking at component ', comp)
			if comp.isStateful:
				new_stmt_list = []
				for stmt1 in comp.codelet.stmt_list:
					stmt = stmt1
					for branch_var in modified_lhses:
						stmt = modify_stmt(stmt, lexer, branch_var)
					new_stmt_list.append(stmt)					
				comp.codelet.stmt_list = new_stmt_list 
			
			if not comp.isStateful:
				new_codelets = []
				for codelet in comp.codelets:
					new_stmt_list = []
					for stmt1 in codelet.stmt_list:
						stmt = stmt1 
						for branch_var in modified_lhses:
							stmt = modify_stmt(stmt, lexer, branch_var)
						new_stmt_list.append(stmt)
					codelet.stmt_list = new_stmt_list 
					new_codelets.append(codelet)
				comp.codelets = new_codelets

	def process_graph(self):
		original_dep_edges = copy.deepcopy(self.dep_graph.edges())
		# print("original_dep_edges")
		#for u, v in original_dep_edges:
			#print("edge")
			#print("u")
			#u.print()
			#print("v")
			#v.print()

		#print("\n Dep graph nodes")
		#for codelet in self.dep_graph.nodes:
		#	print()
		#	codelet.print()

		#print("\n Dep graph stateful nodes")
		#for codelet in self.stateful_nodes:
		#	print()
		#	codelet.print()

		self.dep_graph.remove_nodes_from(self.stateful_nodes)
		# remove incoming and outgoing edges
		# self.dep_graph.remove_edges_from([(w, u) for w in self.dep_graph.predecessors(u)])
		# self.dep_graph.remove_edges_from([(u, v) for v in self.dep_graph.successors(u)])

		i = 0
		codelet_component = {} # codelet repr -> component it belongs to
	
		for u in self.stateful_nodes:
			print("stateful codelet ", i)
			stateful_comp = StatefulComponent(u)
			stateful_comp.set_name('comp_' + str(i))
			self.components.append(stateful_comp)
			codelet_component[str(u)] = stateful_comp
			i += 1
	
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
		#print("\n Original_dep_edges")
		#for u, v in original_dep_edges:
	#		print("edge")
#			print("u")
#			u.print()
#			print("v")
#			v.print()
#		print()
		######

#		print("codelet_component", codelet_component)

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

		#self.write_comp_graph()
		#exit(1)

		#print("------------------------------------------------- transferring components... ------------------------------------")
		#self.transfer_branch_vars()
		#print("------------------------------------------------- transfer components end. ------------------------------------")
		#exit(1)

		print("------------------------------------------------- Merging components... ------------------------------------")
		self.merge_components() 
		print("------------------------------------------------- Merge components end. ------------------------------------")
		#exit(1)
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
		self.write_comp_graph()

	def do_synthesis(self):
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
			result_file = comp.write_sketch_file(self.output_dir, comp_name, self.var_types)
			print("processing sketch output...")
			if comp.isStateful:
				print("processing: output is stateful.")
				self.synth_output_processor.process_single_stateful_output(result_file, comp.outputs[0])
			else:
				print("processing: output is stateless.")
				output_idx = 0
				for file in result_file:
					self.synth_output_processor.process_stateless_output(file, comp.outputs[output_idx])
					output_idx += 1

		self.write_comp_graph()
		# nx.draw(self.comp_graph)

	def write_comp_graph(self):
		f_deps = open(os.path.join(self.output_dir, "deps.txt"), 'w+')
		num_nodes = len(self.comp_graph.nodes)
		f_deps.write("{}\n".format(num_nodes))
		for u, v in self.comp_graph.edges:
			f_deps.write("{} {}\n".format(self.comp_index[u], self.comp_index[v]))
