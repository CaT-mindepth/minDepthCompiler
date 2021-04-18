import sys
import parser
import subprocess

class StatefulSketch:
	def __init__(self, filename, codelet, state_var_info, input_vars):
		self.filename = filename
		self.codelet_stmts = codelet
		self.state_var, self.state_var_type = state_var_info
		self.input_vars = input_vars # list of (var, type)
		self.alu_types = ["pred_raw"]

		# self.check_codelet()

	def write_generators(self, f):

		c = "generator int C() { return ??; }"

		opt = "generator int Opt(int op1) { \n \
	 		bit enable = ??(1); \n \
	  		if (! enable) return 0; \n \
	  			return op1; \n \
			} \n"

		mux2 = "generator int Mux2(int op1, int op2) { \n \
	  		int choice = ??(1); \n \
	  		if (choice == 0) return op1; \n \
	  		else if (choice == 1) return op2; \n \
			} \n"

		mux3 = "generator int Mux3(int op1, int op2, int op3) { \n \
	  	int choice = ??(2); \n \
	  	if (choice == 0) return op1; \n \
	  	else if (choice == 1) return op2; \n \
	  	else if (choice == 2) return op3; \n \
	  	else assert(false); \n \
		} \n"

		rel_op = "generator bit rel_op(int operand1, int operand2) {\n \
		int opcode = ??(2); \n \
		  if (opcode == 0) { \n \
		    return operand1 != operand2; \n \
		  } else if (opcode == 1) { \n \
		    return operand1 < operand2; \n \
		  } else if (opcode == 2) { \n \
		    return operand1 > operand2; \n \
		  } else { \n \
		    assert(opcode == 3); \n \
		    return operand1 == operand2; \n \
		  } \n \
		} \n"

		arith_op = "generator int arith_op(int operand1, int operand2) { \n \
	  	int opcode = ??(1); \n \
	  	if (opcode == 0) { \n \
	    	return operand1 + operand2; \n \
 	  	} else { \n \
	    	assert(opcode == 1); \n \
	    	return operand1 - operand2; \n \
	  	} \n \
		} \n"

		f.write(c)
		f.write(opt)
		f.write(mux2)
		f.write(mux3)
		f.write(rel_op)
		f.write(arith_op)

	def write_codelet(self, f):
		f.write(
			"int codelet({} {}, {} {}, {} {}) {\n".format(self.state_var_type, self.state_var, \
				self.input_vars[0][1], self.input_vars[0][0], self.input_vars[1][1], self.input_vars[1][0])
			)
		for stmt in self.codelet_stmts:
			f.write(stmt + "\n")
		f.write("}\n")

	def write_impl(self, alu_type, f):
		f.write(
			"int {}(int state_0, bit pkt_0, int pkt_1) implements codelet {\n".format(alu_type)
			)
		alu_spec = ""
		if alu_type == "pred_raw":
			alu_spec = "int old_state_0 = state_0;\n \
	if (rel_op(Opt(state_0), Mux3(pkt_0, pkt_1, C()))) {\n \
    state_0 = Opt(state_0) + Mux3(pkt_0, pkt_1, C());\n \
	}\n \
    return Mux2(old_state_0, state_0);\n"
		else:
			pass

		assert(alu_spec != "")

		f.write(alu_spec)
		f.write("}\n")

	def write_sketch(self, alu_type, f):
		self.write_generators(f)
		self.write_codelet(f)
		self.write_impl(alu_type, f)

	def check_codelet(self):
		solved = False
		for alu_type in self.alu_types:
			sketch_filename = self.filename + "_" + self.state_var + "_" + alu_type + ".sk"
			f = open(sketch_filename, "w+")
			self.write_sketch(alu_type, f)
			f.close()
			# run Sketch
			sketch_outfilename =  sketch_filename + ".out"
			print("sketch %s > %s" % (sketch_filename, sketch_outfilename))

			f_sk_out = open(sketch_outfilename, "w+")

			print("running sketch, ALU: {}".format(alu_type))
			print("sketch_filename", sketch_filename)
			ret_code = subprocess.call(["sketch", sketch_filename], stdout=f_sk_out)
			if ret_code == 0: # successful
				print("Solved")
				solved = True
				break
			else:
				print("Failed")
		
			f_sk_out.close()

		if not solved:
			print("Codelet cannot be implemented by any stateful ALUs")
			
	


