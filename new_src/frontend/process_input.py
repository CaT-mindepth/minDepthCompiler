
from overrides import overrides
from .. import pass_manager


class ProcessInput(pass_manager.Pass):
    var_types = {}  # key: variable, value: type
    stmt_map = {}  # key: lhs var, value: list of assignment statements
    tmp_vars = {}  # key: tmp var, value: rhs
    tmp_vars_rev = {}  # reverse map of tmp_vars
    rhs_map = {}  # rhs, lhs
    state_variables = set()

    def __init__(self, pm):
        super().__init__("ProcessInput", ["ReadInFile"], pm)
        self.tmp_cnt = 0

    @overrides
    def run(self, deps):
        state_var = False
        lines = deps[0].get_output()
        f_idx = 0
        line = lines[f_idx]
        while line != "# declarations end\n":
            # store type information
            if line == "# state variables start\n":
                state_var = True
            elif line == "# state variables end\n":
                state_var = False
            else:
                line = line.rstrip()
                line = line.replace(";", "")
                toks = line.split(" ")
                assert (len(toks) == 2)
                var_name = toks[1].rstrip()
                self.var_types[var_name] = toks[0]

                if state_var:  # state variable. TODO: make this more general
                    self.state_variables.add(var_name)

            f_idx += 1
            line = lines[f_idx]

    @overrides
    def get_output(self):
        return {'state_variables' : self.state_variables, 'var_types' : self.var_types}