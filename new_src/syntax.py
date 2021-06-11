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



class Codelet:
	def __init__(self, stmts=[]):
		self.stmt_list = stmts

	def get_stmt_list(self):
		return self.stmt_list

	def add_stmts(self, stmts):
		self.stmt_list.extend(stmts)

	def replace_char(self, char_old, char_new):
		for stmt in self.stmt_list:
			stmt.replace_char(char_old, char_new)

	def is_stateful(self, state_vars): # TODO: avoid recomputing this each time
		for stmt in self.stmt_list:
			if stmt.is_stateful:
				self.stateful = True
				self.state_var = stmt.get_state_var(state_vars)
				return True

		self.stateful = False
		return False

	def get_state_pkt_field(self):
		# print("get_state_pkt_field")
		for stmt in self.stmt_list:
			# stmt.print()
			if stmt.write_flank:
				# print("write flank")
				return stmt.state_pkt_field_final # read or write flank should have been called for stmt before this

		assert(False)

	def get_inputs(self): # Make inputs and outputs class variables?
		defines = [stmt.lhs for stmt in self.stmt_list]
		uses = [rhs for stmt in self.stmt_list for rhs in stmt.rhs_vars]
		# an input is a use which has no define in the codelet
		inputs = []
		if self.stateful: # state_var is always an input for a stateful codelet
			inputs.append(self.state_var)
		
		inputs.extend([u for u in uses if u not in defines])

		return inputs

	def get_state_var(self):
		assert(self.stateful)
		return [self.get_state_pkt_field()]

	def get_outputs(self):
		# all defines are outputs (may or may not be used by subsequent codelets)
		return [stmt.lhs for stmt in self.stmt_list]

	def print(self):
		for stmt in self.stmt_list:
			stmt.print()
	
	def __str__(self):
		return " ".join(s.get_stmt() for s in self.stmt_list)
