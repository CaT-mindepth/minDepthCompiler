from .. import syntax
from .. import pass_manager
from overrides import overrides
from ..syntax import *
import logging


class GenDependencyGraph(pass_manager.Pass):

    def __init__(self, pm: pass_manager.PassManager):
        super().__init__("GenDependencyGraph", ["ReadInFile", "ProcessInput"])
        pm.register(self)

    @overrides
    def run(self, deps):
        self.lines = deps[0].get_output()

        pi_ = deps[1].get_output()
        self.state_variables = pi_['state_variables']
        self.var_types = pi_['var_types']

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
        self.process_input()
        self.find_dependencies()
        self.build_dependency_graph()
        self.remove_read_write_flanks()

    def process_input(self):
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

            logging.debug(line)
            lhs = line[:assign_idx].strip()
            rhs = line[assign_idx+1:].strip().replace(";", "")
            logging.debug("lhs", lhs, "rhs", rhs)
            stmt = Statement(lhs, rhs, i)
            self.stmt_list.append(stmt)
            self.stmt_map[lhs] = stmt

            logging.debug("state_vars", self.state_variables)

            # read, write flanks
            is_read_flank, state = stmt.is_read_flank(self.state_variables)
            if is_read_flank:
                logging.debug("read flank")
                self.read_write_flanks[state]["read"] = stmt

            is_write_flank, state = stmt.is_write_flank(
                self.state_variables)
            if is_write_flank:
                logging.debug("write flank")
                self.read_write_flanks[state]["write"] = stmt

            self.depends[stmt] = []
            self.define_use[stmt] = set()
            self.use_define[stmt] = set()

            i += 1

    def find_dependencies(self):
        for stmt1 in self.stmt_list:
            for stmt2 in self.stmt_list:
                if stmt1 == stmt2:
                    continue

                # RAW
                if stmt1.lhs in stmt2.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)
                    logging.debug("RAW", stmt1.get_stmt(), stmt2.get_stmt())
                    self.define_use[stmt1].add(stmt2)
                    self.use_define[stmt2].add(stmt1)

                # WAR
                elif stmt2.lhs in stmt1.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)

                # WAW
                elif stmt1.lhs == stmt2.lhs and (stmt1.line_no < stmt2.line_no):
                    assert(False)  # shouldn't exist in SSA form

        logging.debug("read_write_flanks", self.read_write_flanks)
        for state_var, read_write in self.read_write_flanks.items():
            read_flank = read_write["read"]
            write_flank = read_write["write"]
            logging.debug("read_flank", read_flank, "write_flank", write_flank)
            self.depends[read_flank].append(write_flank)
            self.depends[write_flank].append(read_flank)

    def print_dependencies(self):
        for s, stmts in self.depends.items():
            s.print()
            print("depends")
            for st in stmts:
                st.print()
            print()

    def find_dependencies(self):
        logging.debug("finding dependencies")

        for stmt1 in self.stmt_list:
            for stmt2 in self.stmt_list:
                if stmt1 == stmt2:
                    continue

                # RAW
                if stmt1.lhs in stmt2.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)
                    logging.debug("RAW", stmt1.get_stmt(), stmt2.get_stmt())
                    self.define_use[stmt1].add(stmt2)
                    self.use_define[stmt2].add(stmt1)

                # WAR
                elif stmt2.lhs in stmt1.rhs_vars and (stmt1.line_no < stmt2.line_no):
                    self.depends[stmt1].append(stmt2)

                # WAW
                elif stmt1.lhs == stmt2.lhs and (stmt1.line_no < stmt2.line_no):
                    assert(False)  # shouldn't exist in SSA form

        logging.debug("read_write_flanks", self.read_write_flanks)
        for state_var, read_write in self.read_write_flanks.items():
            read_flank = read_write["read"]
            write_flank = read_write["write"]
            logging.debug("read_flank", read_flank, "write_flank", write_flank)
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
            self.read_write_edges.add((read_c, write_c))
            self.read_write_edges.add((write_c, read_c))

        self.condense_phi_nodes()

    def remove_read_write_flanks(self):
        for state_var, read_write in self.read_write_flanks.items():
            read_flank = read_write["read"]
            write_flank = read_write["write"]

    def condense_phi_nodes(self):
        print("condense phi nodes")
        phi_nodes_list = []  # (u, v, new node)

        for u1, v1 in self.dep_graph.edges:
            assert(len(u1.stmt_list) == 1)
            assert(len(v1.stmt_list) == 1)
            u = u1.get_stmt_list()[0]
            v = v1.get_stmt_list()[0]
            if ":" in u.rhs and ":" in v.rhs:  # both u and v are phi nodes
                print("u lhs", u.lhs, "v lhs", v.lhs)
                same_var = True
                state_var = False

                pkt_state_var_prefix = ["p_" + x for x in self.state_variables]
                print(pkt_state_var_prefix)
                for prefix in pkt_state_var_prefix:
                    # skip state var phi nodes
                    if u.lhs.startswith(prefix) or v.lhs.startswith(prefix):
                        state_var = True
                        break

                # check if u.lhs and v.lhs refer to the same program variable. TODO: make this more general
                # may not work for some variable names, eg. pkt1, pkt12.
                # SSA vars pkt120 (20, pkt1) and pkt120 (0, pkt12) are indistinguishable
                # TODO: SSA var = var + "_" + idx
                i = 0
                common_prefix = ""  # longest common prefix
                mismatched_chars = []
                while i < len(u.lhs) and i < len(v.lhs):
                    if (u.lhs[i] == v.lhs[i]):
                        common_prefix += u.lhs[i]
                    # mismatched character is not a digit, so not the same variable
                    elif (not u.lhs[i].isdigit()) or (not v.lhs[i].isdigit()):
                        same_var = False

                    i += 1

                if (not state_var) and same_var:
                    print(u, v)
                    print("same var")
                    u_cond_var, u_br1, u_br2 = u.tokenize_phi_node()
                    v_cond_var, v_br1, v_br2 = v.tokenize_phi_node()

                    # definition of cond_var
                    u_cond = self.stmt_map[u_cond_var].rhs
                    v_cond = self.stmt_map[v_cond_var].rhs

                    if v_cond == "!"+u_cond_var or v_cond == "!"+u_cond:
                        print("branch var, neg branch var")
                        new_lhs = v.lhs
                        new_cond = u_cond_var
                        new_br1 = u_br1
                        new_br2 = v_br1
                        new_rhs = "{} ? {} : {}".format(
                            new_cond, new_br1, new_br2)
                        # new_phi_node = Codelet(["{} = {};".format(new_lhs, new_rhs)])
                        new_phi_node = Codelet(
                            [Statement(new_lhs, new_rhs, -1)])

                        phi_nodes_list.append((u1, v1, new_phi_node))

        for u, v, new_phi_node in phi_nodes_list:
            print("nodes", self.dep_graph.nodes)
            self.dep_graph.add_node(new_phi_node)

            out_nbrs = [x for x in self.dep_graph.successors(u) if x != v] + \
                [x for x in self.dep_graph.successors(v)]

            in_nbrs = [x for x in self.dep_graph.predecessors(u)] + \
                [x for x in self.dep_graph.predecessors(v) if x != u]

            self.dep_graph.add_edges_from(
                [(new_phi_node, n) for n in out_nbrs])
            self.dep_graph.add_edges_from([(m, new_phi_node) for m in in_nbrs])

            self.dep_graph.remove_node(u)
            self.dep_graph.remove_node(v)
