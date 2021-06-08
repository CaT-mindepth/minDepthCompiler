

from .. import pass_manager 
from overrides import overrides 

class DepGraphDCE(pass_manager.Pass):

    def __init__(self, pm : pass_manager.PassManager):
        super().__init__("DepGraphDCE", ["GenDepGraph"], pm)
        pm.register(self)
    
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

    @overrides 
    def run(self, deps):
        pass # TODO

    @overrides 
    def get_output(self):
        pass # TODO