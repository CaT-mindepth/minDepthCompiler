from .. import syntax 
from .. import pass_manager

class GenDependencyGraph(pass_manager.Pass):


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

		# self.stmt_map = {} # key: lhs var, value: (rhs_vars, line_no, stmt)
		# self.stmt_list = [] # list of statements
		# self.stmt_validity = {} # key:statement value: flag, flag is 0 if statement is to be deleted

		self.process_input()
		self.find_dependencies()
		# self.remove_dead_code()
		self.build_dependency_graph()
		self.remove_read_write_flanks()
		self.build_SCC_graph()

		# self.process_stateful_nodes()


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
			read_flank = read_write["read"]
			write_flank = read_write["write"]
			print("read_flank", read_flank, "write_flank", write_flank)
			self.depends[read_flank].append(write_flank)
			self.depends[write_flank].append(read_flank)

		# self.print_dependencies()


	def remove_dead_code(self):
		# print("Dead code elimination")
		i = len(self.stmt_list)-1
		it = 0
		while True:
			changed = False
			while i >= 0:
				stmt = self.stmt_list[i]
				if self.temp_stmt(stmt) and ((stmt not in self.define_use) or (len(self.define_use[stmt]) == 0)):
					# temp stmt is not used, mark it to be deleted
					# print("%s not used" % stmt)
					self.stmt_validity[stmt] = 0
					# remove stmt wherever it occurs in the value of define_use
					if stmt in self.use_define:
						for defn in self.use_define[stmt]:
							self.define_use[defn].remove(stmt)
							self.depends[defn].remove(stmt)
							changed = True
				i -= 1

			it += 1
			print("Finished %d iterations" % it)
			if changed == False:
				print("Done, took %d iterations." % it)
				break

	def write_optimized_code(self, outputfile):
		print("Writing optimized code after dead code elimination")
		# print("stmt_list", self.stmt_list)
		f_out = open(outputfile+"_opt", "w+")
		for stmt in self.stmt_list:
			# print(stmt)
			if self.stmt_validity[stmt] == 1:
				f_out.write(stmt)

		f_out.close()

	def temp_stmt(self, stmt):
		lhs = stmt.split('=')[0].rstrip()
		if lhs.startswith("tmp"):
			return True
		else:
			return False

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
			self.read_write_edges.add((read_c, write_c))
			self.read_write_edges.add((write_c, read_c))

		self.condense_phi_nodes()

		self.draw_graph(self.dep_graph, self.inputfilename + "_dep")

		# self.contract_cycles()


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
					if (e[0] in scc) and (e[1] in scc) and (e not in self.read_write_edges): # both nodes in scc, not a rw flank edge
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


	def remove_read_write_flanks(self):
		for state_var, read_write in self.read_write_flanks.items():
			read_flank = read_write["read"]
			write_flank = read_write["write"]


	def condense_phi_nodes(self):
		print("condense phi nodes")
		phi_nodes_list =  [] # (u, v, new node)
		
		for u1, v1 in self.dep_graph.edges:
			assert(len(u1.stmt_list) == 1)
			assert(len(v1.stmt_list) == 1)
			u = u1.get_stmt_list()[0]
			v = v1.get_stmt_list()[0]
			if ":" in u.rhs and ":" in v.rhs: # both u and v are phi nodes
				print("u lhs", u.lhs, "v lhs", v.lhs)
				same_var = True
				state_var = False

				pkt_state_var_prefix = ["p_" + x for x in self.state_variables]
				print(pkt_state_var_prefix)
				for prefix in pkt_state_var_prefix:
					if u.lhs.startswith(prefix) or v.lhs.startswith(prefix): # skip state var phi nodes
						state_var = True
						break

				# check if u.lhs and v.lhs refer to the same program variable. TODO: make this more general
				# may not work for some variable names, eg. pkt1, pkt12.
				# SSA vars pkt120 (20, pkt1) and pkt120 (0, pkt12) are indistinguishable
				# TODO: SSA var = var + "_" + idx
				i = 0
				common_prefix = "" # longest common prefix
				mismatched_chars = []
				while i < len(u.lhs) and i < len(v.lhs):
					if (u.lhs[i] == v.lhs[i]):
						common_prefix += u.lhs[i]
					elif (not u.lhs[i].isdigit()) or (not v.lhs[i].isdigit()): # mismatched character is not a digit, so not the same variable
							same_var = False
						
					i += 1

				if (not state_var) and same_var:
					print(u, v)
					print("same var")
					u_cond_var, u_br1, u_br2 = u.tokenize_phi_node()
					v_cond_var, v_br1, v_br2 = v.tokenize_phi_node()


					u_cond = self.stmt_map[u_cond_var].rhs # definition of cond_var
					v_cond = self.stmt_map[v_cond_var].rhs
					

					if v_cond == "!"+u_cond_var or v_cond == "!"+u_cond:
						print("branch var, neg branch var")
						new_lhs = v.lhs
						new_cond = u_cond_var
						new_br1 = u_br1
						new_br2 = v_br1
						new_rhs = "{} ? {} : {}".format(new_cond, new_br1, new_br2)
						# new_phi_node = Codelet(["{} = {};".format(new_lhs, new_rhs)])
						new_phi_node = Codelet([Statement(new_lhs, new_rhs, -1)])

						phi_nodes_list.append((u1, v1, new_phi_node))


		for u, v, new_phi_node in phi_nodes_list:
			print("nodes", self.dep_graph.nodes)
			self.dep_graph.add_node(new_phi_node)

			out_nbrs = [x for x in self.dep_graph.successors(u) if x != v] + \
				[x for x in self.dep_graph.successors(v)]

			in_nbrs = [x for x in self.dep_graph.predecessors(u)] + \
				[x for x in self.dep_graph.predecessors(v) if x != u]

			self.dep_graph.add_edges_from([(new_phi_node, n) for n in out_nbrs])
			self.dep_graph.add_edges_from([(m, new_phi_node) for m in in_nbrs])

			self.dep_graph.remove_node(u)
			self.dep_graph.remove_node(v)

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
