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
        # use this only after calling both is_read_flank and is_write_flank
        self.is_stateful = False
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

                if "[" in tok.value:  # array variable
                    array_index = tok.value[tok.value.find(
                        "[")+1: tok.value.find("]")]
                    # TODO: tokenize array_index; could be an expression
                    self.rhs_vars.append(array_index)

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
                r = r[:r.find("[")]  # array name

            if r in state_vars:
                self.is_stateful = True
                self.read_flank = True
                self.state_var = r  # Check: works for for array types?
                self.state_pkt_field_init = self.lhs
                return (True, r)

        return (False, "")

    def is_write_flank(self, state_vars):
        l = self.lhs
        if is_array_var(l):
            l = l[:l.find("[")]  # array name

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
        br1 = self.rhs[self.rhs.find("?")+1: self.rhs.find(":")].strip()
        br2 = self.rhs[self.rhs.find(":")+1:].strip()

        return (cond, br1, br2)

    def replace_char(self, char_old, char_new):
        self.lhs = self.lhs.replace(char_old, char_new)
        self.rhs = self.rhs.replace(char_old, char_new)

    def is_stateful(self, state_vars):  # TODO: avoid computing this each time
        # Only read and write flanks are considered stateful statements
        return (self.is_read_flank(state_vars) or self.is_write_flank(state_vars))

    def get_state_var(self, state_vars):
        (is_read, var_r) = self.is_read_flank(state_vars)
        (is_write, var_w) = self.is_write_flank(state_vars)
        assert(is_read or is_write)  # stmt must be stateful
        state_var = var_r
        if is_write:
            state_var = var_w

        return state_var

    def __eq__(self, other):
        if other == None:
            return False 
        return self.lhs == other.lhs and self.rhs == other.rhs and self.line_no == other.line_no

    def __hash__(self):
        return str(self).__hash__()


class Codelet:
    def __init__(self, stmts=[]):
        self.stmt_list = stmts
        self.state_vars = []
        # Initialized to stateful ALU output after splitting transformation (see split_SCC_graph).
        self.stateful_output = None
        self.stateful = False # initially make this false

    def get_stmt_list(self):
        return self.stmt_list
    

    def get_write_flank_deps(self, write_flank):
        deps = []
        read_flank = None
        for st in self.stmt_list:
            if st.read_flank:
                read_flank = st.lhs
                continue
            if st.write_flank:
                if st.rhs_vars[0] != write_flank:
                    return None, []
                break 
            if st.read_flank != None:
                deps.append(st)

        return read_flank, deps

    """
		returns 3-tuple of <stmts in BCI (in reverse order)>, <list of read flanks>, <list of write flanks>
		The union of the two latest variables form the PI of the BCI.
	"""

    def get_stmt_deps(self, st1):
        assert st1 in self.stmt_list
        ps = []
        print(' statement: ', st1)
        print(' rhs_vars: ', st1.rhs_vars)
        print(' state vars: ', self.state_vars)

        # do not return the read/write flanks themselves
        if st1.read_flank:
            return [], [st1.lhs], []

        if self.is_output_write_flank(st1.lhs):
            return [], [], [st1.lhs]

        # for every statement in list, test if it is
        # st1's dependency. If it is, add it and return.
        st1_rhs_deps = set(st1.rhs_vars)
        deps_ret = [st1]
        # add all statements until (not including) st1 to list
        for st2 in self.stmt_list:
            if st2 == st1:
                break
            ps.append(st2)
        ps.reverse()

        read_flanks = []
        write_flanks = []

        for st2 in ps:
            if st2.lhs in st1_rhs_deps:
                if st2.read_flank:
                    read_flanks.append(st2.lhs)
                elif self.is_output_write_flank(st2.lhs):
                    write_flanks.append(st2.lhs)
                else:
                    deps_ret.append(st2)
                    for var in st2.rhs_vars:
                        if not (var in self.state_vars):
                            st1_rhs_deps.add(var)
        return deps_ret, read_flanks, write_flanks

    def get_last_stmt_of_output(self, output):
        stmt = None
        for s in self.stmt_list:
            if s.lhs == output:
                stmt = s
        return stmt

    # decide if output var is write_flank. Also used in split_SCC_graph.
    def is_output_write_flank(self, output):
        for s in self.stmt_list:
            if s.write_flank:
                if output in s.rhs_vars:
                    return True
        return False

    # decide if output var is read_flank. Also used in split_SCC_graph.
    def is_output_read_flank(self, output):
        for s in self.stmt_list:
            if s.read_flank:
                if output == s.lhs:
                    return True
        return False

    # get BCIs for each output variable.
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
                o_last_stmt = self.get_last_stmt_of_output(o)
                m[o] = self.get_stmt_deps(o_last_stmt)
        return m

    def get_stmt_of(self, var):
        for s in self.stmt_list:
            if var == s.lhs:
                return s 

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

    def is_stateful(self, state_vars):  # TODO: avoid recomputing this each time
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
        self.state_vars = list(set(self.state_vars))  # deduplicate
        return self.stateful

    def get_state_pkt_field(self):
        # print("get_state_pkt_field")
        all_flanks = set()
        for stmt in self.stmt_list:
            # stmt.print()
            if stmt.write_flank:
                # print("write flank")
                # read or write flank should have been called for stmt before this
                all_flanks.add(stmt.state_pkt_field_final)
            if stmt.read_flank:
                all_flanks.add(stmt.state_pkt_field_init)
        # we're guaranteed to have one read/write flank.
        return list(all_flanks)

    def get_inputs(self):  # Make inputs and outputs class variables?
        defines = [stmt.lhs for stmt in self.stmt_list]
        uses = [rhs for stmt in self.stmt_list for rhs in stmt.rhs_vars]
        # an input is a use which has no define in the codelet
        inputs = []
        if self.stateful:  # state_var is always an input for a stateful codelet
            # inputs.append(self.state_var)
            inputs = list(set(self.state_vars))  # deduplicate

        inputs.extend([u for u in uses if u not in defines])

        return list(set(inputs))

    def get_outputs(self):
        # all defines are outputs (may or may not be used by subsequent codelets)
        if self.stateful_output == None:
            return list(set([stmt.lhs for stmt in self.stmt_list]))
        else:
            # Post split_SCC_graph operation.
            # return set of state vars + self.stateful_output
            # we include all state vars because this is an assumption in
            # the resource graph.
            return self.state_vars + [self.stateful_output]
    
    # used by write_{domino|tofino}_sketch_spec in synthesis.py for getting defines.
    def get_defines(self):
        return list(set([stmt.lhs for stmt in self.stmt_list]))

    def print(self):
        for stmt in self.stmt_list:
            stmt.print()
    
    def get_code_as_string(self):
        return " ".join(list(map(str, self.stmt_list)))

    def __str__(self):
        if self.stateful:
            print('codelet ', " ".join(list(map(str, self.stmt_list))), ' is stateful')
            return " ".join(list(map(str, self.stmt_list))) + " [stateful output =" + str(self.stateful_output) + "]"
        else:
            return " ".join(list(map(str, self.stmt_list)))

class DependencyGraph:
    def __init__(self, filename, state_vars, var_types, stateful_grammar="tofino", eval = False):
        self.inputfilename = filename
        self.state_variables = state_vars
        self.var_types = var_types
        self.outputfilename = filename + "_3addr_code"

        self.eval = eval

        self.stmt_list = []  # list of statements
        # key: lhs var, value: stmt (value is unique since input is in SSA)
        self.stmt_map = {}
        # key: state variable, value: {"read":read_flank, "write":write flank}
        self.read_write_flanks = {s: {} for s in self.state_variables}
        self.codelets = []  # list of codelets
        self.stateful_nodes = set()  # stateful nodes

        self.define_use = {}  # key: stmt, value: list of statements which use lhs of key
        self.use_define = {}  # reverse map of define_use
        self.depends = {}  # key: stmt, value: list of stmts which depend on key

        self.stateful_grammar = stateful_grammar

        self.process_input()
        self.find_dependencies()
        self.build_dependency_graph()
        self.build_SCC_graph()
        print('----calling split_SCC_graph---')
        self.split_SCC_graph()

    def process_input(self):
        f = open(self.inputfilename)
        self.lines = f.readlines()  # read from preprocessed file

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

                # RAW
                if stmt1.lhs in stmt2.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)
                    print("RAW", stmt1.get_stmt(), stmt2.get_stmt())
                    self.define_use[stmt1].add(stmt2)
                    self.use_define[stmt2].add(stmt1)

                # WAR
                elif stmt2.lhs in stmt1.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)

                # WAW
                elif stmt1.lhs == stmt2.lhs and (stmt1.line_no < stmt2.line_no):
                    assert(False)  # shouldn't exist in SSA form

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

        codelets = {}  # key:stmt, value:codelet for stmt
        for stmt in self.stmt_list:
            codelet = Codelet([stmt])
            codelets[stmt] = codelet

        for stmt, codelet in codelets.items():
            # if self.stmt_validity[stmt] == 1:
            self.dep_graph.add_node(codelet)
            self.dep_graph.add_edges_from(
                [(codelet, codelets[s]) for s in self.depends[stmt]])

        self.read_write_edges = set()
        for state_var, read_write in self.read_write_flanks.items():
            read_flank = read_write["read"]
            write_flank = read_write["write"]
            read_c = codelets[read_flank]
            write_c = codelets[write_flank]
            # self.read_write_edges.add((read_c, write_c))
            # This is the extra edge from write flank to read flank, not to be taken as a RAW dependency.
            self.read_write_edges.add((write_c, read_c))

        self.draw_graph(self.dep_graph, self.inputfilename + "_dep")

    """
	Code for splitting stateless expressions in stateful nodes
	when necessary (this might hold, for DominoIfElseRawALU for instance.)
	"""

    # The _actual_ outputs of node u. Only includes necessary outputs
    # Does not include e.g. stateful variables in u.
    def get_SCC_graph_outputs(self, u):
        successor_inputs = set()
        used_outputs = set()

        for v in self.scc_graph.successors(u):
            for i in v.get_inputs():
                successor_inputs.add(i)

        for o in u.get_outputs():
            if o in successor_inputs:
                used_outputs.add(o)

        return used_outputs

    def split_SCC_graph(self):
        import grammar_util
        import copy
        initial_nodes = list(self.scc_graph.nodes)

        # duplicate_stateful_node maps one output flank to a possibly
        # newly created duplicate of the current stateful node, with a total
        # of #flanks - 1 such creations (the 0th flank is assigned to the current node.)
        # After this function call, the current codelet's stateful_output field will
        # possibly get marked. If the codelet is sink, then stateful_output field will
        # remain None.
        # returns flank_to_codelet, v_out_neighbors
        def duplicate_stateful_node(v, v_outputs, bcis, fake_flanks=set()):
            print('size of SCC graph pre-duplicate: ', len(self.scc_graph.nodes))


            # We can map every stateful register.
            # Step 1: Gather all the flanks.
            flanks = set()
            for o in v_outputs:
                # Note that even if o is a flank, it must be in either read_flanks or write_flanks.
                _, read_flanks, write_flanks = bcis[o]
                
                print('output ', o, '   read_flanks: ', read_flanks, '  write_flanks: ', write_flanks)

                flanks.update(read_flanks)
                flanks.update(write_flanks)

            # Take into account potential "fake flanks,"
            # when there are extra stateful registers left over, we can treat
            # some of the stateless output variables as flanks by doing
            # their computation in a stateful register.
            flanks.update(fake_flanks)

            print('flanks: ', flanks)

            # Step 2: For each additional flank, create a parallel codelet
            # that outputs exactly that flank.
            flanks = list(flanks)
            # Check if current node is sink. If that happens, skip the
            # current node. Nothing to output.
            if len(flanks) == 0:
                return {}, []
            # Otherwise we need to output all the flanks. Assign one parallel codelet
            # per flank for a total of len(flanks) - 1 new parallel codelets we create.
            flank_to_codelet = {}
            for flank in flanks[1:]:
                # create a copy of v.
                print('   - createing a node for flank ', flank)
                vp = copy.deepcopy(v)
                self.scc_graph.add_node(vp)
                self.codelets.append(vp)
                self.stateful_nodes.add(vp)
                # add edges
                for u in self.scc_graph.predecessors(v):
                    self.scc_graph.add_edge(u, vp)
                # only add edges to those that require flank as inputs.
                for w in self.scc_graph.successors(v):
                    if flank in w.get_inputs():
                        self.scc_graph.add_edge(vp, w)
                vp.stateful_output = flank
                flank_to_codelet[flank] = vp
            # assign current codelet to flanks[0].
            print('   - createing a node for flank ', flanks[0])
            v.stateful_output = flanks[0]
            flank_to_codelet[flanks[0]] = v
            # once we assigned v to flanks[0], delete out-edges to nodes that don't require flanks[0].
            # but before we do this, memorize the existing out-neighbors of v since we'll need them in step 3.
            v_out_neighbors = list(self.scc_graph.successors(v))
            for w in v_out_neighbors:
                if not (flanks[0] in w.get_inputs()):
                    self.scc_graph.remove_edge(v, w)

            print('size of SCC graph post-duplicate: ', len(self.scc_graph.nodes))
            return flank_to_codelet, v_out_neighbors


        def parse_bci_deps(stmts):
            g = nx.DiGraph()
            
            lhs_to_node = {}
            stmt_to_codelet = {}
            node_inputs = {}

            # add stmt to graph as nodes
            for stmt in stmts:
                stmt_codelet = Codelet([ stmt ])                
                g.add_node(stmt_codelet)
                lhs_to_node[stmt.lhs] = stmt_codelet 
                stmt_to_codelet[stmt] = stmt_codelet

                # add stmt_codelet to node_inputs[rhs] for every rhs
                for rhs in stmt.rhs_vars:
                    if rhs in node_inputs:
                        node_inputs[rhs].append(stmt_codelet)
                    else:
                        node_inputs[rhs] = [ stmt_codelet ]

            # add dependencies based on stmt rhs
            for stmt in stmts:
                for rhs in stmt.rhs_vars:
                    if rhs in lhs_to_node: # otherwise rhs is an input
                        g.add_edge(lhs_to_node[rhs], stmt_to_codelet[stmt])

            return g, node_inputs, lhs_to_node


        def find_codelet(codelet):
            print('finding node for codelet: ', str(codelet))
            for node in self.scc_graph:
                if str(node) == str(codelet):
                    return node
            return None

        # Function for assigning stateless logic in node `v` into predecessor nodes after step 2 of case 3 (see above).
        def split_stateless_bcis(v, v_outputs, v_out_neighbors, flank_to_codelet, fake_flanks=set()):
            # Step 3: iterate through each output with the map `bcis`, possibly create new
            # successors depending on which flank its PI is.
            # By virtue of construction of v_outputs, every element in it is a stateless
            # lhs that is used in a successor of u.
            #  a) o is a flank. Do not create additional nodes.
            #  b) o is not a flank. So we create an additional node.
            for o in v_outputs:
                bci, read_flanks, write_flanks = bcis[o]
                # o is a flank iff bci == [].
                if bci == [] or o in fake_flanks:
                    pass  # taken care of
                else:
                    # create new codelets from BCI.
                    bci_stmts = copy.deepcopy(bci)
                    bci_stmts.reverse()

                    stmt_subgraph, node_inputs, lhs_to_node = parse_bci_deps(bci_stmts)
                    stmt_nodes = {}
                    # add nodes in stmt_subgraph to self.scc_graph
                    for stmt_codelet in stmt_subgraph:
                        node = find_codelet(stmt_codelet)
                        print('adding stmt : ', stmt_codelet)
                        print('find_codelet for stmt : ', node)
                        if node == None:
                            self.scc_graph.add_node(stmt_codelet)
                            stmt_nodes[stmt_codelet] = stmt_codelet
                        else:
                            stmt_nodes[stmt_codelet] = node
                    print('-----------number of nodes in the graph: ', len(self.scc_graph.nodes))
                    # add edges in stmt_subgraph to self.scc_graph
                    for (u_stmt, v_stmt) in stmt_subgraph.edges:
                        self.scc_graph.add_edge(stmt_nodes[u_stmt], stmt_nodes[v_stmt])
                    print('---------------number of nodes in the graph: ', len(self.scc_graph.nodes))

                    # create inputs/outputs from added region via a helper codelet
                    co = Codelet(stmts=bci_stmts)
                    co_inputs = co.get_inputs()
                    # add in-edges to co using flank_to_codelet.
                    flanks = set(read_flanks + write_flanks)
                    # add edge from stateful copy of v outputting flank, to stateless node depending on it.
                    for flank in flanks:
                        for stmt_codelet in node_inputs[flank]:
                            self.scc_graph.add_edge(flank_to_codelet[flank], stmt_nodes[stmt_codelet])
                    
                    # add an edge for every required input from v's predecessors.
                    for input in co_inputs:
                        if not (input in flanks):
                            for pred in self.scc_graph.predecessors(v):
                                if input in pred.get_outputs():
                                    for stmt_codelet in node_inputs[input]:
                                        self.scc_graph.add_edge(pred, stmt_nodes[stmt_codelet])

                    # add out-edges
                    for u in v_out_neighbors:
                        if o in u.get_inputs():
                            self.scc_graph.add_edge(stmt_nodes[lhs_to_node[o]], u)


        print(' ---- split_SCC_graph ----- ')
        for v in initial_nodes:
            if v.stateful:
                # calculate number of outputs
                v_outputs = self.get_SCC_graph_outputs(v)
                num_outputs = len(v_outputs)  # won't include state vars, but
                num_statevars = len(v.state_vars)

                print(' -------------- v_outputs: ', v_outputs)
                for out in v_outputs:
                    if v.is_output_read_flank(out):
                        print(out, ' is read flank')
                    if v.is_output_write_flank(out):
                        print(out, ' is write flank')

                # query for number of stateful ALUs
                num_stateful_registers = grammar_util.num_statefuls[self.stateful_grammar]

                # Case 0: Fits within a stateful ALU. No need to do anything.
                if len(v_outputs) == 1 \
                    and (v.is_output_write_flank(list(v_outputs)[0]) or v.is_output_read_flank(list(v_outputs)[0])) \
                    and num_statevars <= num_stateful_registers:
                    v.stateful_output = list(v_outputs)[0]
                    print('everything fits within a stateful ALU. No need to do anything.')
                    continue
                
                if len(v_outputs) == 0 and num_statevars <= num_stateful_registers:
                    print('everything fits within a stateful ALU (no outputs). No need to do anything.')
                    continue

                print("elements in v_outputs: ", v_outputs)

                # Case 1: Too many stateful variables. Can't synthesize in this case
                if num_statevars > num_stateful_registers:
                    print(
                        'Error: cannot synthesize program, too many stateful variables in a Codelet.')
                    exit(1)

                # Case 2

                # Case 2(a): stateful variables < num_stateful_registers.
                # Backfill stateful registers using candidates from v_outputs
                # that aren't read flanks or write flanks.
                fake_flanks = set()

                print('Number of state variables: ', num_statevars)
                print('NUmber of stateful registers: ', num_stateful_registers)
                print('State variables: ', v.state_vars)

                if num_statevars < num_stateful_registers:
                    print('Case 2(a) triggered. ')
                    """
                    avail_state_regs = num_stateful_registers - num_statevars
                    while avail_state_regs > 0:
                        fill = None
                        for x in v_outputs:
                            if not (v.is_output_read_flank(x)) and not (v.is_output_write_flank(x)):
                                fill = x
                                break
                        if fill == None:
                            # Every output is a read/write flank.
                            # Nothing more to fill stateful registers with. Break
                            break
                        else:
                            print(' - found a fill: ', fill)
                            avail_state_regs -= 1
                            num_statevars += 1
                            v_outputs.remove(fill)
                            fake_flanks.add(fill)
                    """
                    # For now, we create parallel stateful ALUs for every stateless output and treat them as flanks.
                    for x in list(v_outputs):
                        if (not (v.is_output_read_flank(x))) and (not (v.is_output_write_flank(x))):
                            fake_flanks.add(x)
                            v_outputs.remove(x)
                # Found all fake flanks. Call duplicate_stateful_node using them
                # and return.
                print('all fills found. they are: ', fake_flanks)
                bcis = v.get_stateless_output_partitions()
                flank_to_codelet, v_out_neighbors = duplicate_stateful_node(v, v_outputs, bcis, fake_flanks=fake_flanks)
                # If there are outputs left over, we have no choice but to split
                # them into stateless successors.
                split_stateless_bcis(
                    v, v_outputs, v_out_neighbors, flank_to_codelet, fake_flanks=fake_flanks)
        print('number of SCC nodes post splitting: ', len(self.scc_graph.nodes))
        self.draw_graph(self.scc_graph, self.inputfilename + "_splitted_dag")

    def build_SCC_graph(self):  # strongly connected components
        i = 0
        self.scc_graph = nx.DiGraph()
        sccs = []  # list of sccs (list of codelets)

        node_scc = {}  # key: combined node, value: scc
        codelet_node = {}  # key: codelet, value: combined node for scc it belongs to

        for scc in nx.strongly_connected_components(self.dep_graph):
            print("SCC", i)
            sccs.append(scc)

            g = nx.DiGraph()
            g.add_nodes_from(scc)
            scc_edges = []
            for v in scc:
                for e in self.dep_graph.edges([v]):
                    # both nodes in scc, not a w flank -> r flank edge
                    if (e[0] in scc) and (e[1] in scc) and (e not in self.read_write_edges):
                        scc_edges.append(e)

            g.add_edges_from(scc_edges)

            # IMP: need to explicitly initialize with [], otherwise old value of combined_node persists
            combined_node = Codelet([])
            for v in nx.topological_sort(g):
                print("v", v, "stmts len", len(v.stmt_list))
                assert(len(v.stmt_list) == 1)  # each codelet has one stmt
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
                self.scc_graph.add_edges_from([(node, codelet_node[v]) for v in self.dep_graph.successors(u)
                                               if node != codelet_node[v]])
                self.scc_graph.add_edges_from([(codelet_node[w], node) for w in self.dep_graph.predecessors(u)
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
        idx = 0
        for node in graph.nodes:
            stmt_list = node.get_stmt_list()
            stmt_text = str(idx) + "; " + " ".join([s.get_stmt().replace(":", "|")
                                 for s in stmt_list])
            if node.is_stateful and node.stateful_output != None:
                stmt_text += " [stateful output=" + node.stateful_output + "]"
            dot.node(stmt_text)
            node_stmts[node] = stmt_text
            idx += 1
        print('total number of nodes created: ', idx)
        for (u, v) in graph.edges:
            dot.edge(node_stmts[u], node_stmts[v])

        if not self.eval:
            dot.render(graphfile, view=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 dependencyGraph.py <input file> <output file>")
        exit(1)

    inputfile = sys.argv[1]
    outputfile = sys.argv[2]

    dep_graph_obj = DependencyGraph(inputfile)
    dep_graph_obj.write_optimized_code(outputfile)
