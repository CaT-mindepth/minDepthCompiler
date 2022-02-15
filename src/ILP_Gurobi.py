import sys
import gurobipy as gp
from gurobipy import GRB

class ILP_ActionInfo(object):
    # represents ALU dependencies in a single action (resp. table)
    def __init__(self, table_name, action_name, num_alus, alus, alu_adjacency_list):
        self.table_name = table_name 
        self.action_name = action_name
        self.num_alus = num_alus 
        self.alu_adjacency_list = alu_adjacency_list
        self.alus = alus

    def get_num_alus(self):
        return self.num_alus 

    def get_table_action_pair(self):
        return (self.table_name, self.action_name)

    # returns a list of edges in the ALU dependency graph.
    def get_dependency_list(self):
        deps = []
        for src_alu_id in range(len(self.alu_adjacency_list)):
            for tgt_alu in self.alu_adjacency_list[src_alu_id]:
                tgt_alu_id = tgt_alu.id 
                print(' * gen_dependency_list: dependency between ', src_alu_id, ' and ', tgt_alu_id)
                deps.append((src_alu_id, tgt_alu_id))
        return deps

class ILP_TableDeps(object):
    def __init__(self, match_deps, action_deps, successor_deps, reverse_deps):
        self.match_deps = match_deps 
        self.action_deps = action_deps 
        self.successor_deps = successor_deps 
        self.reverse_deps = reverse_deps 

class ILP_TableInfo(object):
    # represents ALU dependencies in a single action (resp. table)
    # If this constructor is caleld, multi_table_mode is set to false.
    def __init__(self, table_name, num_alus, alus, alu_adjacency_list):
        self.table_name = table_name 
        self.num_alus = num_alus 
        self.alu_adjacency_list = alu_adjacency_list
        self.alus = alus
        self.multi_table_mode = False 

    # alternatively, read in from multiple action infos.
    # If this constructor is called, multi_table_mode is set to true. 
    # table_action_map: map from table name (str) to list of actions (list[str])
    #def __init__(self, table_dependencies : ILP_TableDeps, table_action_map : dict[str, list[str]], action_infos : dict[str, list[ILP_ActionInfo]]):
    #    self.action_infos = action_infos 
    #    self.multi_table_mode = True 
    #    self.table_dependencies = table_dependencies 
    #    self.table_action_map = table_action_map
        

    def get_num_alus(self):
        return self.num_alus 

    # returns a list of edges in the ALU dependency graph.
    def get_dependency_list(self):
        deps = []
        for src_alu_id in range(len(self.alu_adjacency_list)):
            for tgt_alu in self.alu_adjacency_list[src_alu_id]:
                tgt_alu_id = tgt_alu.id 
                print(' * gen_dependency_list: dependency between ', src_alu_id, ' and ', tgt_alu_id)
                deps.append((src_alu_id, tgt_alu_id))
        return deps

    def get_multi_table_info(self):
        assert self.multi_table_mode == True 
        alu_dep_dic = {}
        alu_dic = {}
        table_list = []
        for table in self.table_action_map: 
            alu_dep_dic[table] = [] # empty dependency list 
            alu_dic[table] = len(self.table_action_map)
            table_list.append(table)
            for action in self.table_action_map[table]:
                alu_dep_dic[table] += self.action_infos[action] # actions 
        return alu_dic, alu_dep_dic, table_list 
        
    def multi_table_ILP(self):
        alu_dic, alu_dep_dic, table_list = self.get_multi_table_info()
        return gen_and_solve_ILP(self.table_dependencies.match_deps, self.table_dependencies.action_deps, \
            self.table_dependencies.successor_deps, self.table_dependencies.reverse_deps, alu_dic, alu_dep_dic, table_list)

    # do ILP
    def ILP(self, stats=None):
        # def gen_and_solve_ILP(match_dep, action_dep, successor_dep, reverse_dep, alu_dic, alu_dep_dic, table_list):
        # match_dep: [(u, v)], where u and v are table names
        # action_dep: ...
        # successor_dep: ...
        # reverse_dep:  ...
        # alu_dic : map from table name to the number of ALUs in each table
        # alu_dep_dic: map from table name to dependency (edge) list between ALUs in each table
        # table_list: list of tables
        if stats != None:
            stats.start_ilp()
        a=None
        if self.multi_table_mode:
            a = self.multi_table_ILP()
        else:
            a = gen_and_solve_ILP([], [], [], [], {self.table_name:len(self.alu_adjacency_list)}, {self.table_name: self.get_dependency_list()}, [self.table_name] )
        if stats != None:
            stats.end_ilp()
            a.find_number_of_stages()
            a.compute_alus_per_stage()
            stats.update_num_stages(a.num_stages)
            stats.update_num_alus(self.num_alus)
            num_statefuls = len(list(filter(lambda x: x.get_type() == 'STATEFUL', self.alus)))
            stats.update_num_stateful_alus(num_statefuls)
            stats.update_num_stateless_alus(self.num_alus - num_statefuls)
            stats.update_num_alus_per_stage(list(map(lambda x: len(x), a.alus_per_stage)))
        return a


class ILP_MultiTable():
    """
            self.table_name = table_name 
        self.num_alus = num_alus 
        self.alu_adjacency_list = alu_adjacency_list
        self.alus = alus
        self.multi_table_mode = False 
        """
    #def __init__(self, table_dependencies : ILP_TableDeps, table_action_map : dict[str, list[str]], action_infos : dict[str, list[ILP_ActionInfo]]):
    def __init__(self, table_dependencies, table_action_map, action_infos):

        self.action_infos = action_infos 
        self.multi_table_mode = True 
        self.table_dependencies = table_dependencies 
        self.table_action_map = table_action_map
        self.alus = []
        for table_name in self.action_infos:
            self.alus += self.action_infos[table_name].alus
        

    def get_num_alus(self):
        return self.num_alus 

    # returns a list of edges in the ALU dependency graph.
    def get_dependency_list(self):
        deps = []
        for src_alu_id in range(len(self.alu_adjacency_list)):
            for tgt_alu in self.alu_adjacency_list[src_alu_id]:
                tgt_alu_id = tgt_alu.id 
                print(' * gen_dependency_list: dependency between ', src_alu_id, ' and ', tgt_alu_id)
                deps.append((src_alu_id, tgt_alu_id))
        return deps

    def get_multi_table_info(self):
        assert self.multi_table_mode == True 
        alu_dep_dic = {}
        alu_dic = {}
        table_list = []
        #action_deps = self.get_dependency_list()
        for table in self.table_action_map: 
            alu_dep_dic[table] = [] # empty dependency list 
            table_list.append(table)
            num_alus = 0
            for action_name in self.table_action_map[table]:
                actionObj = self.action_infos[action_name]
                num_alus += actionObj.get_num_alus()
                action_dep_list = actionObj.get_dependency_list()
                alu_dep_dic[table] += action_dep_list
                #print(self.action_infos)
                #x = self.action_infos[action]
                #alu_dep_dic[table] += [ x ] # actions 
            alu_dic[table] = num_alus
        return alu_dic, alu_dep_dic, table_list 
        
    def multi_table_ILP(self):
        alu_dic, alu_dep_dic, table_list = self.get_multi_table_info()
        return gen_and_solve_ILP(self.table_dependencies.match_deps, self.table_dependencies.action_deps, \
            self.table_dependencies.successor_deps, self.table_dependencies.reverse_deps, alu_dic, alu_dep_dic, table_list)

    # do ILP
    def ILP(self, stats=None):
        # def gen_and_solve_ILP(match_dep, action_dep, successor_dep, reverse_dep, alu_dic, alu_dep_dic, table_list):
        # match_dep: [(u, v)], where u and v are table names
        # action_dep: ...
        # successor_dep: ...
        # reverse_dep:  ...
        # alu_dic : map from table name to the number of ALUs in each table
        # alu_dep_dic: map from table name to dependency (edge) list between ALUs in each table
        # table_list: list of tables
        if stats != None:
            stats.start_ilp()
        a=None
        if self.multi_table_mode:
            a = self.multi_table_ILP()
        else:
            assert(False)

class ILP_Output(object):
    """
        ILP_Output: represents the output of an ILP program.
        Will be filled during gen_and_solve ILP and returned.
    """

    def __init__(self, num_tables):
        # tables: contains a dict mapping each ALU id to a stage
        self.tables = [{} for i in range(num_tables)] # table -> [collection of alus]
        self.optimal = False 
    
    def add_stage_info(self, var_name, stage):
        # var name format: T3_A_3 -> 1
        exploded = var_name.split("_")
        assert len(exploded) == 3
        table_number = int(exploded[0][1])
        alu_id = int(exploded[2])
        self.tables[table_number][alu_id] = stage 

    def get_alu_stage(self, table_num, alu_id):
        print(' > get_alu_stage: table ', table_num, ', alu_id = ', alu_id, ': ', self.tables[table_num][alu_id])
        return int(self.tables[table_num][alu_id])

    # is Gurobi output optimal. If it isn't, then this instance
    # will contain a blank table assignment.
    def optimal_status(self, op):
        self.optimal = op 


    def find_number_of_stages(self):
        max_stages = 0
        for actions in self.tables:
            for action in actions: 
                stage = actions[action]
                max_stages = max(max_stages, stage)
        max_stages = int(max_stages)
        self.num_stages = max_stages + 1
        return max_stages + 1
    

    def compute_alus_per_stage(self):
        self.find_number_of_stages()
        print('number of stages: ', self.num_stages)
        self.alus_per_stage = [[] for i in range(self.num_stages)]
        max_alus_per_stage = 0
        for actions in self.tables:
            for action in actions:
                stage = actions[action]
                print('stage: ', stage)
                print('action: ', action)
                print("num stages: ", len(self.alus_per_stage))
                self.alus_per_stage[int(stage)].append(action)
        
        for alus_list in self.alus_per_stage: 
            max_alus_per_stage = max(max_alus_per_stage, len(alus_list))
        
        self.max_alus_per_stage = max_alus_per_stage 
    
# ruijief: we modify gen_and_solve_ILP to return an ILP_Output object.
def gen_and_solve_ILP(match_dep, action_dep, successor_dep, reverse_dep, alu_dic, alu_dep_dic, table_list):
    # Create a new model
    m = gp.Model("ILP")

    # Create variables

    # Get the match and alu list
    z3_match_list = []
    for t in table_list:
        z3_match_list.append(m.addVar(name='%s_M' % t, vtype=GRB.INTEGER))
    # print(z3_match_list)
    z3_alu_list = []
    print('ILP_Gurobi: alu_dic = ', alu_dic)
#    for t in table_list:
#        for i in range(1, int(alu_dic[t]) + 1):
#            print('ILP_Gurobi: Adding var ', '%s_A_%s' % (t, i))
#            z3_alu_list.append(m.addVar(name='%s_A_%s' % (t, i), vtype=GRB.INTEGER))
    # ruijief: change to use 0-based indexing scheme
    for t in table_list:
        for i in range(int(alu_dic[t])):
            print('ILP_Gurobi: Adding var ', '%s_A_%s' % (t, i))
            z3_alu_list.append(m.addVar(name='%s_A_%s' % (t, i), vtype=GRB.INTEGER))

    # print(z3_alu_list)
    # z3_match_list = [Int('%s_M' % t) for t in table_list]
    # z3_alu_list = [Int('%s_A_%s' % (t, i)) for t in table_list for i in range(1, int(alu_dic[t]) + 1)]

    total_stage = 12
    # z3_alu_loc_vec is a list of 0/1 which specifies which stage this ALU is at
    z3_alu_loc_vec = []
    for t in table_list:
        #for i in range(1, int(alu_dic[t]) + 1): # ruijief: change to use 0-based indexing
        for i in range(int(alu_dic[t])):
            new_v = []
            for k in range(total_stage):
                new_v.append(m.addVar(name="%s_A%s_stage_%s" % (t, i, k), vtype=GRB.INTEGER))
            z3_alu_loc_vec.append(new_v)
    # z3_alu_loc_vec = [[Int('%s_A_%s_stage_%s' % (t, i, k)) for k in range(total_stage)] for t in table_list for i in range(1, int(alu_dic[t]) + 1)]
    z3_alu_loc_vec_transpose = [[z3_alu_loc_vec[i][j] for i in range(len(z3_alu_loc_vec))] for j in range(len(z3_alu_loc_vec[0]))]
    # print(z3_alu_loc_vec)
    # print(z3_alu_loc_vec_transpose)

    # ref solution:h ttps://support.gurobi.com/hc/en-us/community/posts/360059768191-GurobiError-No-variable-names-available-to-index
    m.update()
    # Constraint 1: Match happens before any action 
    # for t in table_list:
    #    for i in range(1, int(alu_dic[t]) + 1):
    #        m.addConstr('%s_M' % t <='%s_A_%s' % (t, i))
    '''
    for t in table_list:
        for i in range(1, int(alu_dic[t]) + 1):
            m.addConstr(m.getVarByName('%s_M' % t) <= m.getVarByName('%s_A_%s' % (t, i)))
    '''
    # match_then_action_c = [And(Int('%s_M' % t) <= Int('%s_A_%s' % (t, i))) for t in table_list for i in range(1, int(alu_dic[t]) + 1)]

    # Constraint 2: All stage numbers cannot be greater than total available stage
    # TODO: set the total available stage as the parameter
    # For now, we just assume the total available stages is 12
    for match_s in z3_match_list:
        m.addConstr(match_s >= 0)
        m.addConstr(match_s <= total_stage - 1)
    for alu_s in z3_alu_list:
        m.addConstr(alu_s >= 0)
        m.addConstr(alu_s <= total_stage - 1)
    # match_stage_c = [And(match_s >= 0, match_s < total_stage) for match_s in z3_match_list]
    # alu_stage_c = [And(alu_s >= 0, alu_s < total_stage) for alu_s in z3_alu_list]

    # TODO: set the total number of available ALUs per stage to be a parameter
    # For now, we just assume the total available ALUs per stage is 2
    avail_alu = 16

    # Constraint 3: alu-level dependency
    print('ILP_Gurobi: alu_dep_dic: ', alu_dep_dic)
    for key in alu_dep_dic:
        for pair in alu_dep_dic[key]:
            m.addConstr(m.getVarByName('%s_A_%s' % (key, pair[0])) <= m.getVarByName('%s_A_%s' % (key, pair[1])) - 1)
    # Constraint 4: An ALU must be allocated to one and exactly one block

    for i in range(len(z3_alu_list)):
        for k in range(total_stage):
            # Note: model.addConstr((x == 1) >> (y + z <= 5)); LHS must be == 1
            m.addConstr((z3_alu_loc_vec[i][k]==1) >> (z3_alu_list[i] == k))
    # alu_pos_rel_c = []
    for i in range(len(z3_alu_loc_vec)):
        for j in range(len(z3_alu_loc_vec[0])):
            m.addConstr(z3_alu_loc_vec[i][j] >= 0)
    for i in range(len(z3_alu_loc_vec)):
        m.addConstr(sum(z3_alu_loc_vec[i]) == 1)
    for i in range(len(z3_alu_loc_vec_transpose)):
        m.addConstr(sum(z3_alu_loc_vec_transpose[i]) <= avail_alu)
    # Constraint 5: set a variable cost which is our objective function whose value is >= to any other vars
    cost = m.addVar(name='cost', vtype=GRB.INTEGER)
    for m_v in z3_match_list:
        m.addConstr(cost >= m_v)
    for alu_v in z3_alu_list:
        m.addConstr(cost >= alu_v)

    # TODO:Constraint 6: constraints for match, action, successor and reverse dep
    for ele in match_dep:
        t1 = ele[0]
        t2 = ele[1]
        #for i in range(1, int(alu_dic[t1]) + 1): #ruijief: change to use 0-based indexing
        for i in range(int(alu_dic[t])):
            m.addConstr(m.getVarByName('%s_A_%s' % (t1, i)) <= m.getVarByName('%s_M' % t2) - 1)
    for ele in action_dep:
        t1 = ele[0]
        t2 = ele[1]
        # ruijief: change to use 0-based indexing
        #for i in range(1, int(alu_dic[t1]) + 1):
        #    for j in range(1, int(alu_dic[t2]) + 1):
        for i in range(alu_dic[t1]):
            for i in range(alu_dic[t2]):
                m.addConstr(m.getVarByName('%s_A_%s' % (t1, i)) <= m.getVarByName('%s_A_%s' % (t2, j)) - 1)
                # action_dep_c.append(And(Int('%s_A_%s' % (t1, i)) < Int('%s_A_%s' % (t2, j))))
    # successor_dep_c = []
    # reverse_dep_c = []
    print("Come here------------------------")
    # Set objective
    m.setObjective(cost, GRB.MINIMIZE)
    m.optimize()
    if m.status == GRB.OPTIMAL:    
        print('Optimal objective: %g' % m.objVal)
        print("Following is the result we want:*****************")
        for v in m.getVars():
            if v.varName.find('stage') == -1 and v.varName[-1] != 'M' and v.varName != 'cost':
                print('%s %g' % (v.varName, v.x))
        print("************************************************")
        print('Obj: %g' % m.objVal)
    else:
        print("Sad")
    #for v in m.getVars():
    #    print("%s %g" % (v.varName, v.x))
    #print("Obj: %g" % m.objVal)
    '''
    opt.add(match_then_action_c + 
            match_stage_c + alu_stage_c +
            alu_level_c + 
            alu_pos_rel_c + alu_pos_val_c + alu_row_sum_c + alu_col_sum_c +
            cost_with_match_c + cost_with_alu_c + 
            match_dep_c + action_dep_c + successor_dep_c + reverse_dep_c)
    '''
    # TODO: output the layout of ALU grid
    # ruijief:
    # here we return an ILP_Output object.
    output = ILP_Output(len(table_list))
    if m.status == GRB.OPTIMAL:
        output.optimal_status(True)
        for v in m.getVars():
            if v.varName.find('stage') == -1 and v.varName[-1] != 'M' and v.varName != 'cost':
                output.add_stage_info(v.varName, v.x)
    else:
        output.optimal_status(False)
    return output


def main(argv):
    """main program."""
    """Format: python3 ILP_Gurobi.py <filename>"""
    if len(argv) != 2:
        print("Usage: python3 " + argv[0] + " <Dep+Act filename>")
        sys.exit(1)
    filename = argv[1]
    f = open(filename, "r")
    table_list = []
    match_dep = []
    action_dep = []
    successor_dep = []
    reverse_dep = []
    alu_dic = {} # key: table name; val: total number of alus
    alu_dep_dic = {} # key: table name; val: list of alu dep
    while 1:
        line = f.readline()
        if line: 
            # Remove the last '\n'
            line = line[:-1]
            print(line)
            if line == "Table Info:":
                # Get Table Info
                while 1:
                    line = f.readline()
                    line = line[:-1]
                    if line == "Dep Info:":
                        break
                    table_list.append(line)
            # Get Dep Info
            while 1:
                line = f.readline()
                line = line[:-1]
                if line == "Action Info:":
                    break
                sen_list = line.split()
                # Format: T1 has Match dependency relationship with T2
                table1 = sen_list[0]
                table2 = sen_list[-1]
                dep_type = sen_list[2]
                if dep_type == 'Match':
                    match_dep.append([table1, table2])
                elif dep_type == 'Action':
                    action_dep.append([table1, table2])
                elif dep_type == 'Successor':
                    successor_dep.append([table1, table2])
                else:
                    assert dep_type == 'Reverse', "Unrecongnizable dependency type"
                    reverse_dep.append([table1, table2])
            # Get Act Info
            while 1:
                line = f.readline()
                if line:
                    # Format: T1:5;(1,2);(3,4);(4,5)
                    line = line[:-1]
                    table_name = line.split(':')[0]
                    line = line.split(':')[1]
                    print("line = ", line)
                    alu_num = line.split(';')[0]
                    alu_dic[table_name] = alu_num
                    # No alu-level dep if there is only one alu
                    if line.split(';')[1] == '':
                        continue
                    alu_dep_list = line.split(';')
                    print("len(alu_dep_list) =", alu_dep_list)
                    for i in range(1, len(alu_dep_list)):
                        pair = alu_dep_list[i]
                        # pair is in the format: (1,2)
                        pair = pair[1:]
                        pair = pair[:-1]
                        node1 = pair.split(',')[0]
                        node2 = pair.split(',')[1]
                        if alu_dep_dic.get(table_name) == None:
                            alu_dep_dic[table_name] = []
                        alu_dep_dic[table_name].append([node1, node2])
                else:
                    break
        else:
            break
    print("alu_dic = ", alu_dic)
    # Example output: alu_dic =  {'T1': '5'}
    print("alu_dep_dic = ", alu_dep_dic)
    # Example output: alu_dep_dic =  {'T1': [['1', '2'], ['1', '3'], ['2', '4'], ['3', '5']]
    print("table_list = ", table_list)
    # Generate ILP input with format 
    gen_and_solve_ILP(match_dep, action_dep, successor_dep, reverse_dep, alu_dic, alu_dep_dic, table_list)

if __name__ == "__main__":
        main(sys.argv)
