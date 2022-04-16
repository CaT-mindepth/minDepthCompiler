import sys
import ply.lex as lex
import lexerRules
import networkx as nx
from graphviz import Digraph
import stateful

def is_array_var(v):
		return ("[" in v)

class Statement:
	def __init__(self, lhs, rhs, line_no):
		self.lhs = lhs
		self.rhs = rhs
		self.line_no = line_no
		self.find_rhs_vars()
		self.is_stateful = False # use this only after calling both is_read_flank and is_write_flank
		self.read_flank = False
		self.write_flank = False
		self.state_var = ""

	def __str__(self):
		return self.lhs + ' = ' + self.rhs

	def find_rhs_vars(self):
		self.rhs_vars = []
		lexer = lex.lex(module=lexerRules)
		lexer.input(self.rhs)

		for tok in lexer:
			if tok.type == 'ID':
				self.rhs_vars.append(tok.value)

				if "[" in tok.value: # array variable
					array_index = tok.value[tok.value.find("[")+1 : tok.value.find("]")]
					self.rhs_vars.append(array_index) # TODO: tokenize array_index; could be an expression

	def get_stmt(self):
		return "{} = {};".format(self.lhs, self.rhs)

	def print(self):
		print("{} = {};".format(self.lhs, self.rhs))

	def is_read_flank(self, state_vars):
		# if len(self.rhs_vars) == 1:

		print(' is_read_flank: processing rhs_vars = ', self.rhs_vars)
		# if len(self.rhs_vars) > 0: # TODO: ruijief: we changed it to below
		if len(self.rhs_vars) == 1:
			r = self.rhs_vars[0]
			if is_array_var(r):
				r = r[:r.find("[")] # array name

			if r in state_vars:
				self.is_stateful = True
				self.read_flank = True
				self.state_var = r # Check: works for for array types?
				self.state_pkt_field_init = self.lhs
				return (True, r)
			
		return (False, "")

	def is_write_flank(self, state_vars):
		l = self.lhs
		if is_array_var(l):
			l = l[:l.find("[")] # array name

		if l in state_vars:
			self.is_stateful = True
			self.write_flank = True
			# self.state_var = l
			self.state_pkt_field_final = self.rhs
			return (True, l)
		else:
			return (False, "")

	def is_phi_node(self):
		return ("?" in self.rhs and ":" in self.rhs)

	def tokenize_phi_node(self):
		assert(self.is_phi_node())

		cond = self.rhs[: self.rhs.find("?")].strip()
		br1 = self.rhs[self.rhs.find("?")+1 : self.rhs.find(":")].strip()
		br2 = self.rhs[self.rhs.find(":")+1 :].strip()

		return (cond, br1, br2)

	def replace_char(self, char_old, char_new):
		self.lhs = self.lhs.replace(char_old, char_new)
		self.rhs = self.rhs.replace(char_old, char_new)

	def is_stateful(self, state_vars): # TODO: avoid computing this each time
		# Only read and write flanks are considered stateful statements
		return (self.is_read_flank(state_vars) or self.is_write_flank(state_vars))

	def get_state_var(self, state_vars):
		(is_read, var_r) = self.is_read_flank(state_vars)
		(is_write, var_w) = self.is_write_flank(state_vars)
		assert(is_read or is_write) # stmt must be stateful
		state_var = var_r
		if is_write:
			state_var = var_w

		return state_var
	
	def __eq__(self, other):
		return self.lhs == other.lhs and self.rhs == other.rhs and self.line_no == other.line_no 

	def __hash__(self):
		return str(self).__hash__()

class Codelet:
	def __init__(self, stmts=[]):
		self.stmt_list = stmts
		self.state_vars = []

	def get_stmt_list(self):
		return self.stmt_list

	def get_stmt_deps(self, st1):
		assert st1 in self.stmt_list
		ps = []
		print(' statement: ', st1)
		print(' rhs_vars: ', st1.rhs_vars)
		print(' state vars: ', self.state_vars)
		st1_rhs_deps = st1.rhs_vars 
		deps_ret = [ st1 ]
		# add all statements before st1 to list
		for st2 in self.stmt_list:
			if st2 != st1:
				ps.append(st2)
			else:
				break
		# for every statement in list, test if it is 
		# st1's dependency. If it is, add it and return.

		 # do not return the read/write flanks themselves

		if st1.read_flank:
			return "read", []

		if st1.write_flank:
			return "write", []

		ps.reverse()

		for st2 in ps:
			print('   -- looking at ', st2)
			if st2.read_flank:
				print('   ... is read flank')
				return "read", deps_ret
			if st2.write_flank:
				print(' ... is write flank')
				return "write", deps_ret.state_vars
			if st2.lhs in st1_rhs_deps:
				deps_ret.append(st2)
		
		print(" error: no read/write flank found for statement ", st1, ' BCI: ', deps_ret)
		assert(False)
	
	def get_last_stmt_of_output(self, output):
		stmt = None
		for s in self.stmt_list:
			if s.lhs == output:
				stmt = s 
		return stmt

	def is_output_write_flank(self, output):
		for s in self.stmt_list:
			if s.write_flank:
				if output in s.rhs_vars:
					return True 
		return False


	def get_stateless_output_partitions(self):
		print('codelet statements in order: ')
		idx = 0 
		for s in self.stmt_list:
			print(idx, ' ', str(s))
			idx += 1

		outputs = self.get_outputs()
		m = {}
		for o in outputs:
			if not (o in self.state_vars):
				print(o, ' not in state vars')
				# we need additional logic to decide whether
				# an output is a write flank, since write flanks 
				# appear as RHSes.
				if  self.is_output_write_flank(o):
					m[o] = 'write', []
				else:
					o_last_stmt = self.get_last_stmt_of_output(o)
					m[o] = self.get_stmt_deps(o_last_stmt)
		return m

	def add_stmts(self, stmts):
		self.stmt_list.extend(stmts)

	def add_stmts_before(self, stmts):
		# for safety
		new_stmts = []
		new_stmts.extend(stmts)
		new_stmts.extend(self.stmt_list)
		self.stmt_list = new_stmts 

	def replace_char(self, char_old, char_new):
		for stmt in self.stmt_list:
			stmt.replace_char(char_old, char_new)

	def is_stateful(self, state_vars): # TODO: avoid recomputing this each time
		# ruijief:
		# This was for Domino ALU. For Tofino ALU we get two
		# stateful updates, and in general we need to support
		# multiple state variables. Hence we change this.
		self.stateful = False
		self.state_vars = []
		for stmt in self.stmt_list:
			if stmt.is_stateful:
				self.stateful = True
				svar = stmt.get_state_var(state_vars)
				self.state_var = svar
				self.state_vars.append(svar)
				self.stateful = True
		self.state_vars = list(set(self.state_vars)) # deduplicate
		return self.stateful

	def get_state_pkt_field(self):
		# print("get_state_pkt_field")
		all_flanks = set()
		for stmt in self.stmt_list:
			# stmt.print()
			if stmt.write_flank:
				# print("write flank")
				all_flanks.add(stmt.state_pkt_field_final) # read or write flank should have been called for stmt before this
			if stmt.read_flank: 
				all_flanks.add(stmt.state_pkt_field_init)
		return list(all_flanks) # we're guaranteed to have one read/write flank.

	def get_inputs(self): # Make inputs and outputs class variables?
		defines = [stmt.lhs for stmt in self.stmt_list]
		uses = [rhs for stmt in self.stmt_list for rhs in stmt.rhs_vars]
		# an input is a use which has no define in the codelet
		inputs = []
		if self.stateful: # state_var is always an input for a stateful codelet
			# inputs.append(self.state_var)
			inputs = list(set(self.state_vars)) # deduplicate
		
		inputs.extend([u for u in uses if u not in defines])

		return list(set(inputs))

	def get_outputs(self):
		# all defines are outputs (may or may not be used by subsequent codelets)
		return list(set([stmt.lhs for stmt in self.stmt_list]))

	def print(self):
		for stmt in self.stmt_list:
			stmt.print()
	
	def __str__(self):
		return " ".join(s.get_stmt() for s in self.stmt_list)

	# overloaded equality operator
	def __eq__(self, other):
		return str(self) == str(other)

	def __hash__(self):
		return str(self).__hash__()

class DependencyGraph:
	def __init__(self, filename, state_vars, var_types):
		self.inputfilename = filename
		self.state_variables = state_vars
		self.var_types = var_types
		self.outputfilename = filename + "_3addr_code"

		self.stmt_list = [] # list of statements
		self.stmt_map = {} # key: lhs var, value: stmt (value is unique since input is in SSA)
		self.read_write_flanks = {s:{} for s in self.state_variables} # key: state variable, value: {"read":read_flank, "write":write flank}
		self.codelets = [] # list of codelets
		self.stateful_nodes = set() # stateful nodes

		self.define_use = {} # key: stmt, value: list of statements which use lhs of key
		self.use_define = {} # reverse map of define_use
		self.depends = {} # key: stmt, value: list of stmts which depend on key

		self.process_input()
		self.find_dependencies()
		self.build_dependency_graph()
		self.build_SCC_graph()

	def process_input(self):
		f = open(self.inputfilename)
		self.lines = f.readlines() # read from preprocessed file
		
		i = 0
		decls_end = False
		for line in self.lines:
			if line == "# declarations end\n":
				decls_end = True

			if not decls_end:
				continue

			assign_idx = line.find("=")
			if assign_idx == -1:
				continue

			print(line)
			lhs = line[:assign_idx].strip()
			rhs = line[assign_idx+1:].strip().replace(";", "")
			print("lhs", lhs, "rhs", rhs)
			stmt = Statement(lhs, rhs, i)
			self.stmt_list.append(stmt)
			self.stmt_map[lhs] = stmt

			print("state_vars", self.state_variables)

			# read, write flanks
			print('read/write flanks: processing line ', line)
			is_read_flank, state = stmt.is_read_flank(self.state_variables)
			if is_read_flank:
				print("read flank")
				self.read_write_flanks[state]["read"] = stmt

			is_write_flank, state = stmt.is_write_flank(self.state_variables)
			if is_write_flank:
				print("write flank")
				self.read_write_flanks[state]["write"] = stmt

			self.depends[stmt] = []
			self.define_use[stmt] = set()
			self.use_define[stmt] = set()
					
			i += 1

	def print_dependencies(self):
		for s, stmts in self.depends.items():
			s.print()
			print("depends")
			for st in stmts:
				st.print()
			print()

	def find_dependencies(self):
		print("finding dependencies")
		
		for stmt1 in self.stmt_list:
			for stmt2 in self.stmt_list:
				if stmt1 == stmt2:
					continue

				if stmt1.lhs in stmt2.rhs_vars and (stmt1.line_no < stmt2.line_no): # RAW
					self.depends[stmt1].append(stmt2)
					print("RAW", stmt1.get_stmt(), stmt2.get_stmt())
					self.define_use[stmt1].add(stmt2)
					self.use_define[stmt2].add(stmt1)

				elif stmt2.lhs in stmt1.rhs_vars and (stmt1.line_no < stmt2.line_no): # WAR
					self.depends[stmt1].append(stmt2)

				elif stmt1.lhs == stmt2.lhs and (stmt1.line_no < stmt2.line_no): # WAW
					assert(False) # shouldn't exist in SSA form

		print("read_write_flanks", self.read_write_flanks)
		for state_var, read_write in self.read_write_flanks.items():
			print('var: ', state_var)
			print(read_write)
			read_flank = read_write["read"]
			write_flank = read_write["write"]
			print('state_var ', state_var)
			print("read_flank", read_flank)
			print("write_flank", write_flank)
			self.depends[read_flank].append(write_flank)
			self.depends[write_flank].append(read_flank)


	def build_dependency_graph(self):
		self.dep_graph = nx.DiGraph()

		codelets = {} # key:stmt, value:codelet for stmt
		for stmt in self.stmt_list:
			codelet = Codelet([stmt])
			codelets[stmt] = codelet

		for stmt, codelet in codelets.items():
			# if self.stmt_validity[stmt] == 1:
			self.dep_graph.add_node(codelet)
			self.dep_graph.add_edges_from([(codelet, codelets[s]) for s in self.depends[stmt]])

		self.read_write_edges = set()
		for state_var, read_write in self.read_write_flanks.items():
			read_flank = read_write["read"]
			write_flank = read_write["write"]
			read_c = codelets[read_flank]
			write_c = codelets[write_flank]
			# self.read_write_edges.add((read_c, write_c))
			self.read_write_edges.add((write_c, read_c)) # This is the extra edge from write flank to read flank, not to be taken as a RAW dependency.


		self.draw_graph(self.dep_graph, self.inputfilename + "_dep")


	def build_SCC_graph(self): # strongly connected components
		i = 0
		self.scc_graph = nx.DiGraph()
		sccs = [] # list of sccs (list of codelets)

		node_scc = {} # key: combined node, value: scc
		codelet_node = {} # key: codelet, value: combined node for scc it belongs to

		for scc in nx.strongly_connected_components(self.dep_graph):
			print("SCC", i)
			sccs.append(scc)

			g = nx.DiGraph()
			g.add_nodes_from(scc)
			scc_edges = []
			for v in scc:
				for e in self.dep_graph.edges([v]):
					if (e[0] in scc) and (e[1] in scc) and (e not in self.read_write_edges): # both nodes in scc, not a w flank -> r flank edge
						scc_edges.append(e)

			g.add_edges_from(scc_edges)
			
			combined_node = Codelet([]) # IMP: need to explicitly initialize with [], otherwise old value of combined_node persists
			for v in nx.topological_sort(g):
				print("v", v, "stmts len", len(v.stmt_list))
				assert(len(v.stmt_list) == 1) # each codelet has one stmt
				v_text = " ".join([s.get_stmt() for s in v.get_stmt_list()])
				print(v_text)
				combined_node.add_stmts(v.get_stmt_list())
				codelet_node[v] = combined_node
				
			
			self.scc_graph.add_node(combined_node)
			combined_node.is_stateful(self.state_variables)
			node_scc[combined_node] = scc

			i += 1


		# add edges

		for node in self.scc_graph.nodes:
			for u in node_scc[node]:
				self.scc_graph.add_edges_from([(node, codelet_node[v]) for v in self.dep_graph.successors(u) \
							if node != codelet_node[v]])
				self.scc_graph.add_edges_from([(codelet_node[w], node) for w in self.dep_graph.predecessors(u) \
							if codelet_node[w] != node])

		print("SCC graph nodes")
		print(self.scc_graph.nodes)
		for node in self.scc_graph.nodes:
			node.print()
			if node.is_stateful(self.state_variables):
				self.stateful_nodes.add(node)
				print("stateful")


		print("SCC graph stateful nodes", self.stateful_nodes)
		self.draw_graph(self.scc_graph, self.inputfilename + "_dag")
		print("state vars", self.state_variables)

	def draw_graph(self, graph, graphfile):
		dot = Digraph(comment='Dependency graph')
		node_stmts = {}
		for node in graph.nodes:
			stmt_list = node.get_stmt_list()
			stmt_text = " ".join([s.get_stmt().replace(":", "|") for s in stmt_list])
			dot.node(stmt_text)
			node_stmts[node] = stmt_text

		for (u, v) in graph.edges:
			dot.edge(node_stmts[u], node_stmts[v])
		
		dot.render(graphfile, view=True)

if __name__ == "__main__":
	if len(sys.argv) < 3:
		print("Usage: python3 dependencyGraph.py <input file> <output file>")
		exit(1)

	inputfile = sys.argv[1]
	outputfile = sys.argv[2]

	dep_graph_obj = DependencyGraph(inputfile)
	dep_graph_obj.write_optimized_code(outputfile)