from lib2to3.pgen2 import grammar
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
	# ruijief: updated this to make domino preprocessing input work.
	return "br_tmp" in var #var.startswith("p_br_tmp") or var.startswith("pkt_br_tmp") 

class Component: # group of codelets
	def __init__(self, codelet_list, id, 
		grammar_name = None, is_tofino = True):
		self.codelets = codelet_list # topologically sorted
		self.isStateful = False
		self.grammar_name = grammar_name 
		self.is_tofino = is_tofino 
		self.get_inputs_outputs()
		self.set_component_stmts()
    # Here we name each component using comp_{} 
		self.set_name("comp_" + str(id))
		self.bci_inputs = []
		self.bci_outputs = []

	def add_bci_inputs(self, ins):
		self.bci_inputs += (ins)
	
	def add_bci_outputs(self, outs):
		self.bci_outputs += (outs)

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
			f_grammar = open(grammar_util.resolve_stateless(self.is_tofino))
			# copy gramar
			lines = f_grammar.readlines()
			for l in lines:
				f.write(l)

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
				if var_types[v] == "int":
					f.write(" {} |".format(v))
		f.write("};\n")
		f.write("\t}\n")

		if self.is_tofino and not ("bit" not in [var_types[v] for v in self.inputs]): # no inputs of type bit
			print('ERROR: bit present in inputs')
			assert False

		comp_fxn = comp_name + "(" + ", ".join(self.inputs) + ")"

		output_type = var_types[o]
		# TODO: more robust type checking; relational expression can be assigned to an integer variable (should be bool)
		# if output_type == "int":
		# print(' - TODO output type of ', o, ' is int? but it is ', output_type)
		if self.is_tofino and (not (output_type == "int")):
			print('ERROR:bit present as output type')
			assert False
		f.write("\tassert expr(vars, {}) == {};\n".format(bnd, comp_fxn))
		# else:
		# 	assert(output_type == "bit")
		# 	# f.write("\tassert bool_expr(bool_vars, {}) == {};\n".format(bnd, comp_fxn)
		# 	f.write("\tassert bool_expr(vars, bool_vars, {}) == {};\n".format(bnd, comp_fxn)) # TODO: What if there are int and bool vars?

		f.write("}\n")

	def write_sketch_spec_ternary(self, f, var_types, comp_name):
		input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
		spec_name = comp_name
		# write function signature
		f.write("int[2] {}({})".format(spec_name, ", ".join(input_types)) + "{\n")
		# declare output array
		output_array = "_out"
		f.write("\tint[2] {};\n".format(output_array))
		# declare defined variables
		defines = self.codelets[0].get_outputs()
		for v in defines:
			if v not in self.inputs:
				f.write("\t{} {};\n".format(var_types[v], v))
		# function body
		for stmt in self.comp_stmts:
			f.write("\t{}\n".format(stmt.get_stmt()))
		# update output array
		if not(len(self.outputs) <= 2): 
			print('ERROR: outputs are ', self.outputs, ' which is more than 2.')
			assert False
		f.write("\t{}[0] = {};\n".format(output_array, self.outputs[0]))
		if len(self.outputs) > 1:
			f.write("\t{}[1] = {};\n".format(output_array, self.outputs[1]))
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

		f.write(") {\n")
		assert len(self.inputs) <= 4
		f.write('\tint[2] impl = salu(')
		for i in range(len(self.inputs)):
			f.write(self.inputs[i])
			if i < len(self.inputs) - 1:
				f.write(', ')
		if len(self.inputs) < 4:
			fill = 4 - len(self.inputs)
			f.write(', ')
			for _ in range(fill - 1):
				f.write('0, ')
			f.write('0')
		f.write(');\n')

		f.write("\tint [2] spec = {}({});\n".format(comp_name, ', '.join(self.inputs)))

		f.write("\tassert(impl[0] == spec[0]);\n")
		f.write("\tassert(impl[1] == spec[1]);\n") 
		f.write("}\n")



	def write_ternary_sketch_file(self, output_path, comp_name, var_types, stats : test_stats.Statistics = None):
		filenames = []
		for o in self.outputs:
			if stats != None:
				stats.start_synthesis_comp(f"stateless {comp_name} {o}")
			bnd = 1 # start with bound 1, since ALU cannot be a wire (which is bnd 0)
			while True:
				# run Sketch
				sketch_filename = os.path.join(output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk")
				sketch_outfilename = os.path.join(output_path, f"{comp_name}_stateless_{o}_bnd_{bnd}.sk.out")
				f = open(sketch_filename, 'w+')
				self.write_grammar_ternary(f)
				self.write_sketch_spec_ternary(f, var_types, comp_name)
				f.write("\n")
				self.write_sketch_harness_ternary(f, var_types, comp_name)
				f.close()				
				print("sketch {} > {}".format(sketch_filename, sketch_outfilename))
				f_sk_out = open(sketch_outfilename, "w+")
				print("running sketch, bnd = {}".format(bnd))
				print("sketch_filename", sketch_filename)
				ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
				print("return code", ret_code)
				if ret_code == 0: # successful
					if stats != None:
						stats.end_synthesis_comp(f"stateless {comp_name} {o}")
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


	def contains_ternary(self):
		for output in self.outputs:
			if is_branch_var(output):
				return True 
		return False

	def write_sketch_file(self, output_path, comp_name, var_types, stats : test_stats.Statistics = None):
		if self.contains_ternary() and self.is_tofino:
			print('----------- writing ternary sketch file')
			return self.write_ternary_sketch_file(output_path, comp_name, var_types, stats)
		filenames = []
		for o in self.outputs:
			if stats != None:
				stats.start_synthesis_comp(f"stateless {comp_name} {o}")
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
					if stats != None:
						stats.end_synthesis_comp(f"stateless {comp_name} {o}")
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

	def print(self):
		for s in self.comp_stmts:
			s.print()
	
	def __str__(self):
		return " ".join([s.get_stmt() for s in self.comp_stmts])



class StatefulComponent(object):
	def __init__(self, stateful_codelet, grammar_name = None, is_tofino = True):
		self.codelet = stateful_codelet
		self.salu_inputs = {'metadata_lo': 0, 'metadata_hi': 0, 'register_lo': 0, 'register_hi': 0}
		self.isStateful = True
		self.state_vars = stateful_codelet.state_vars # [stateful_codelet.state_var]
		print('-------------------------------------- stateful codelet vars : ', self.state_vars , '--------------***')
		self.state_pkt_fields = stateful_codelet.get_state_pkt_field()
		self.comp_stmts = stateful_codelet.get_stmt_list()
		self.grammar_name = grammar_name
		self.is_tofino = is_tofino
		self.get_inputs_outputs()
		self.bci_inputs = []
		self.bci_outputs = []

	def add_bci_inputs(self, ins):
		self.bci_inputs += ins 
	
	def add_bci_outputs(self, outs):
		self.bci_outputs += outs

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
		TODO: ruijief: I see the issue here --- we can't
			use variable names (e.g. self.last_ssa_var(o)) to distinguish whether a thing is a stateful var or not
			anymore. 
		'''
		redundant_outputs = []
		adj_inputs = [i for c in adj_comps for i in c.inputs]
		print("adj_inputs", adj_inputs)

		for o in self.outputs:
			if o not in self.state_vars:
				if o not in adj_inputs: # not used in adjacent component
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
			if len(self.state_vars) > 1:
				print("Cannot merge stateful component (current component already has 2 state variables)")
				assert(False)
			print(' --my stateful vars: ', self.state_vars)
			print(' --their stateful vars: ', comp.state_vars)
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
					print("Error: Cannot have > 2 state variables in a stateful ALU. Component: ", str(self))
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
					print("Error: Cannot have > 2 metadata fields in a stateful ALU. Component: ", str(self))
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
			print("Failed to open stateful grammar file {}.".format(self.grammar_name))
			exit(1)
		
	def write_domino_sketch_spec(self, f, var_types, comp_name):
		# generate list of arguments 
		input_types = ["{} {}".format(var_types[i], i) for i in self.inputs]
		spec_name = comp_name
		# write function signature
		f.write("int {}({})".format(spec_name, ", ".join(input_types)) + "{\n")
		# declare output array
		spec_ret = "_out"
		f.write("\tint {};\n".format(spec_ret))
		# declare defined variables
		defines = self.codelet.get_outputs()
		for v in defines:
			if v not in self.inputs:
				f.write("\t{} {};\n".format(var_types[v], v))
		# function body
		for stmt in self.comp_stmts:
			f.write("\t{}\n".format(stmt.get_stmt()))
		# update output array
		f.write("\t{} = {};\n".format(spec_ret, self.state_vars[0]))
		# return
		f.write("\treturn {};\n".format(spec_ret))
		f.write("}\n")


	def write_tofino_sketch_spec(self, f, var_types, comp_name):
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

		f.write("\tint[2] impl = salu({}, {}, {}, {});\n".format(
			self.salu_inputs['metadata_lo'], self.salu_inputs['metadata_hi'], self.salu_inputs['register_lo'], self.salu_inputs['register_hi']
		))
		f.write("\tint [2] spec = {}({});\n".format(comp_name, ', '.join(self.inputs)))

		f.write("\tassert(impl[0] == spec[0]);\n")
		f.write("\tassert(impl[1] == spec[1]);\n") 
		f.write("}\n")

	def write_domino_sketch_harness(self, f, var_types, comp_name):
		f.write("harness void sketch(")
		if len(self.inputs) >= 1:
			var_type = var_types[self.inputs[0]]
			f.write("{} {}".format(var_type, self.inputs[0]))

		for v in self.inputs[1:]:
			var_type = var_types[v]
			f.write(", ")
			f.write("{} {}".format(var_type, v))

		f.write(") {\n")

		f.write('\t int impl = salu(')

		num_statefuls = grammar_util.num_statefuls_domino[self.grammar_name]
		num_stateless = grammar_util.num_stateless_domino[self.grammar_name]
		for i in self.input_statevars:
			f.write('{}, '.format(i))
		
		if len(self.input_statevars) < num_statefuls:
			numfill = num_statefuls - len(self.input_statevars)
			for _ in range(numfill):
				f.write('0, ')

		stateless_vars= list(self.input_stateless_vars)
		for i in range(len(stateless_vars)-1):
			f.write('{}, '.format(stateless_vars[i]))

		if len(self.input_stateless_vars) < num_stateless:
			if len(stateless_vars) > 0:
				f.write('{}, '.format(stateless_vars[len(stateless_vars) - 1]))
			numfill = num_stateless - len(self.input_stateless_vars)
			if numfill > 1:
				for _ in range(numfill - 1):
					f.write('0, ')
			f.write('0);\n')
		else:
			if len(stateless_vars) > 0:
				f.write('{});\n'.format( stateless_vars[len(stateless_vars) - 1]))


		f.write("\tint spec = {}({});\n".format(comp_name, ', '.join(self.inputs)))

		f.write("\tassert(impl == spec);\n")
		f.write("}\n")

	def write_sketch_file(self, output_path, comp_name, var_types, prefix="", stats : test_stats.Statistics = None): # TODO: remove bounds from stateful synthesis
		if stats != None:
			stats.start_synthesis_comp(f"stateful {comp_name}")
		sketch_filename = os.path.join(output_path, prefix + f"{comp_name}_stateful.sk")
		sketch_outfilename = os.path.join(output_path, prefix + f"{comp_name}_stateful.sk"+ ".out")
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
			ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
			print("return code", ret_code)
			if ret_code == 0: # successful
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
		return str(self.codelet)

class Synthesizer:
	def __init__(self, state_vars, 
		var_types, dep_graph, stateful_nodes,
		filename, p4_output_name, stats: test_stats.Statistics = None, 
		is_tofino = True, stateless_path = None, stateful_path = None):
		# handle domino grammar generation.
		self.is_tofino = is_tofino 
		self.stateless_path = stateless_path 
		self.stateful_path = stateful_path 

		self.state_vars = state_vars
		self.var_types = var_types
		self.filename = filename
		self.templates_path = "templates"
		self.output_dir = filename
		self.stats = stats
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

		if is_tofino: 
			self.synth_output_processor = SketchOutputProcessor(self.comp_graph)
		else:
			from domino_postprocessor import DominoOutputProcessor
			self.synth_output_processor = DominoOutputProcessor(self.comp_graph)
		
		# 
		if self.stats != None:
			self.stats.start_synthesis()
		
		self.do_synthesis()
		if is_tofino:
			self.synth_output_processor.postprocessing()
			if self.stats != None:
				self.stats.end_synthesis()
			print(self.synth_output_processor.to_ILP_str(table_name="NewTable"))
		else:
			if self.stats != None:
				self.synth_output_processor.postprocessing()
				self.stats.end_synthesis() 
				print("Domino synthesis: ended successfully.")

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
		#try:
		result = new_comp.write_sketch_file(self.output_dir, new_comp.name, self.var_types,\
			 prefix='try_merge_')
		if result == None:
			print('---------- Merge failure. ---------')
			return False
		else:
			print('---------- Merge success. ---------')
			return True
		#except: 
		#	print('AssertionError? failed ')
		#	print('---------- Merge failure. ---------')
		#	return False

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

	def pred_is_branch(self, comp):
		preds = list(self.comp_graph.predecessors(comp))
		return len(preds) == 1 and ((not preds[0].isStateful) and  preds[0].contains_ternary())


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
		#else:
		#	assert list(self.comp_graph.successors(a))[0] == b

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
							if self.stats != None:
								self.stats.incr_num_successful_merges()
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
		return ret, ret_inputs # TODO: deduplicate


	def compute_scc_graph(self):
		# Step 1: Process stateful components. By processing we mean
		# forming a graph of stateful singleton components.
		i = 0
		codelet_component = {} # maps the string of each stateful codelet to the component it belongs to.
		component_inputs = {} # component -> list of codelets that are inputs to that component.
		for u in self.stateful_nodes:
			u.is_stateful(self.state_vars) # initialize state_vars in u
			if self.stateful_path != None:
				stateful_comp = StatefulComponent(u, grammar_name = self.stateful_path, is_tofino = self.is_tofino)
			else:
				stateful_comp = StatefulComponent(u, is_tofino = self.is_tofino)
			stateful_comp.set_name('comp_' + str(i))
			print('compute_scc_graph: StatefulComponent(', stateful_comp.name, '): state vars: ', stateful_comp.state_vars)
			self.components.append(stateful_comp)
			codelet_component[str(u)] = stateful_comp
			i += 1
		# Step 2: Process stateless components. By processing
		# we mean for each principal stateless output, compute its BCI
		# and include everything in its BCI in the stateless component.


		# 2a: process principal outputs (POs).
		principal_outputs = []
		for codelet in self.dep_graph.nodes:
			if not(codelet.is_stateful(self.state_vars)):
				if len(list(self.dep_graph.successors(codelet))) == 0:
					# contains principal outputs. Include it in the list
					principal_outputs.append(codelet)

		print('number of POs: ', len(principal_outputs))

		for codelet in principal_outputs:
			print('processing PO codelet: ', str(codelet))
			bci_nodes, bci_inputs = self.BCI(codelet)
			bci_nodes = list(set(bci_nodes))
			bci_inputs = list(set(bci_inputs)) # dedup.
			if self.stateless_path != None:
				bci_comp = Component(bci_nodes, i, grammar_name = self.stateless_path, is_tofino = self.is_tofino)
			else: 
				bci_comp = Component(bci_nodes, i, is_tofino = self.is_tofino)
			for node in bci_nodes:
				codelet_component[str(node)] = bci_comp
			component_inputs[bci_comp] = bci_inputs
			self.components.append(bci_comp)
			print(' -> stateless PO component: ', bci_comp, ' | id = ', bci_comp.name)
			i += 1 
	
		for comp in self.components:
			if comp.isStateful:
				print(' # state_vars : ', comp.state_vars)

		# 2b:
		# calculate BCIs for stateless outputs that aren't POs. 
		# They occur because as inputs to stateful components.
		for codelet in self.dep_graph.nodes:
			if not(codelet.is_stateful(self.state_vars)) and not (str(codelet) in codelet_component):
				bci_nodes, bci_inputs = self.BCI(codelet)
				bci_nodes = list(set(bci_nodes))
				bci_inputs = list(set(bci_inputs))
				if self.stateless_path != None:
					bci_comp = Component(bci_nodes, i, grammar_name = self.stateless_path, is_tofino = self.is_tofino)
				else:
					bci_comp = Component(bci_nodes, i, is_tofino = self.is_tofino)
				for node in bci_nodes:
					codelet_component[str(node)] = bci_comp 
				self.components.append(bci_comp)
				component_inputs[bci_comp] = bci_inputs 
				i += 1
		# Finally: Build the actual components graph by adding predecessor relations.
		# Stateful components: Add their predecessor codelets' corresponding
		# components as in-neighbors. 
		# Stateless components: Add their input codelets' corresponding components
		# as in-neighbors.
		self.scc_graph = nx.DiGraph()
		for comp in self.components:
			self.scc_graph.add_node(comp)

		for comp in self.components:
			if comp.isStateful:
				# stateful component contains a single (stateful) codelet.
				for pred_codelet in self.dep_graph.predecessors(comp.codelet):
					pred_codelet_comp = codelet_component[str(pred_codelet)]
					self.scc_graph.add_edge(pred_codelet_comp, comp)
					print(': ',pred_codelet_comp.name, ' ->', comp.name)
			else:
				# stateless component. their predecessors come from 
				# corresponding codelets in components_inputs[.] map.
				for pred_codelet in component_inputs[comp]:
					pred_codelet_comp = codelet_component[str(pred_codelet)]
					self.scc_graph.add_edge(pred_codelet_comp, comp)
					print('! ', pred_codelet_comp.name, ' ->', comp.name)
			
		# we leave it to the postprocessor to figure out dependencies between
		# stateless and stateful components.
		print('--------------------- stateless components from BCI --------------------')
		for comp in self.components:
			if comp.isStateful:
				print('------- Stateful Component: ', comp.name)
				print(comp)
				print('# state_vars: ', comp.state_vars)
				print('-------')
			else:
				print('------- Stateless Component: ', comp.name)
				print(comp)
				print('-------')


	def process_graph(self):
		self.state_vars = list(set(self.state_vars))
		self.comp_graph = nx.DiGraph() 
		self.compute_scc_graph()
		#exit(1)
		"""
		original_dep_edges = copy.deepcopy(self.dep_graph.edges())

		self.dep_graph.remove_nodes_from(self.stateful_nodes)
		i = 0
		codelet_component = {} # codelet repr -> component it belongs to

		# create component graph
		print("Add component graph edges")
		#self.comp_graph = nx.DiGraph()
		#self.comp_graph.add_nodes_from(self.components)	
		self.compute_scc_graph() # Here
		for u, v in original_dep_edges: # add edges between components
			if codelet_component[str(u)] != codelet_component[str(v)]:
				self.comp_graph.add_edge(codelet_component[str(u)], codelet_component[str(v)])
				print(str(codelet_component[str(u)]))
				print("->")
				print(str(codelet_component[str(v)]))
				print()
		# Duplicate components to eliminate inputs of type bit (branch variables)
		outputs_comp = {} # output -> component
		"""
		self.comp_graph = self.scc_graph 
		if True: #False: # True: # self.is_tofino:
			print("------------------------------------------------- Merging components... ------------------------------------")
			if self.stats != None:
				self.stats.update_num_components(len(list(self.comp_graph.nodes)))
				self.stats.start_merging()
			self.merge_components() 
			if self.stats != None:
				self.stats.end_merging()
			print("------------------------------------------------- Merge components end. ------------------------------------")
			print(' * number of components in current graph: ', len(list(self.comp_graph.nodes)))
			if self.stats != None:
				self.stats.update_num_postmerge_components(len(list(self.comp_graph.nodes)))
			print('----------------------------------')
		else:
			if self.stats != None:
				self.stats.start_merging()
				self.stats.end_merging()
				self.stats.num_successful_merges = 0
				self.stats.update_num_postmerge_components(len(list(self.comp_graph.nodes)))
			print('Not Tofino Grammar, skipping merge components algorithm...')
		self.comp_index = {} # component -> index
		print("comp index", self.comp_index)
		# check for redundant outputs
		print("Eliminate redundant outputs after merging")
		i = 0
		for comp in nx.topological_sort(self.comp_graph):
			print(' -------- component ', i, ' is this: ', str(comp))
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
			result_file = comp.write_sketch_file(self.output_dir, comp_name, self.var_types, stats = self.stats)
			print("processing sketch output...")
			if comp.isStateful:
				print("processing: output is stateful.")
				self.synth_output_processor.process_single_stateful_output(result_file, comp.outputs[0])
			else:
				if comp.contains_ternary():
					print('processing: output is ternary stateful.')
					for file in result_file:
						self.synth_output_processor.process_single_stateful_output(file, comp.outputs[0])
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
