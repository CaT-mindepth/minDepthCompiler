# populate_j2.py: populates p4 jinja2 template via user-supplied arguments
# Ruijie Fang <ruijief@princeton.edu>

import jinja2 
import os 
import json

# list of all unused variables in tofino_j2 jinja2 template:
# ------------------------------------------------------------
# stateless_alus
#   type: array of size (num_pipeline_stages * num_alus_per_stage)
#   each entry in the array is a dict containing the following entries:
#       { 'enable': type int, either 0 (does not enable) or 1 (enable)
#          'opcode': type int, opcode for the (i,j)-th stateless alu
#               (NOTE: Please use the same opcode for the ones in stateless_alu_for_tofino.alu)
#               | 0 -> modify_field(result, operand0)
#               | 1 -> modify_field(result, operand0)
#               | 2 -> add(result, operand0, operand1)
#               | 3 -> add(result, operand0, immediate_operand)
#               | 4 -> subtract(result, operand1, operand0)
#               | 5 -> subtract(result, operand0, immediate_operand)
#               | 6 -> subtract(result, immediate_operand, operand0)
#               | 7 -> max(result, operand0, opearnd1)
#               | 8 -> max(result, operand0, immediate_operand)
#               | 9 -> min(result, operand0, operand1)
#               | _ -> min(result, operand0, immediate_operand)
#          'operand0': type string, operant0 for the (i,j)-th stateless alu
#          'operand1': type string, operand1 for the (i,j)-th stateless alu
#          'result':   type string, result
#          'immediate_operand': imm for the (i,j)-th stateless alu
#       }
#  
# stateful_alus: dict array of size (num_pipeline_stages * num_state_groups)
#   stateful_alus[i][j] contains a dict with the following entries:
#       { condition_lo_expr
#         condition_hi_expr
#         update_lo_1_predicate_expr
#         update_lo_1_value_expr
#         update_lo_2_predicate_expr
#         update_lo_2_value_expr
#         update_hi_1_predicate_expr
#         update_hi_1_value_expr
#         update_hi_2_predicate_expr
#         update_hi_2_value_expr
#         output_value_expr
#         output_dst
#       }
#       all of them are type string.
# sketch_name: 
#   type string, name of the sketch file, which will be prefix of the name of
#   the stateful alu blackboxes in the p4 program.
# num_alus_per_stage:
#   type int, number of alus per stage, parametrizes the number of columns in the stateless_alus array.
# salu_configs:
#   array of size (num_pipeline_stages * num_state_groups), each entry has type int and can be 0 or 1.
#   if salu_configs[i][j] == 1, then in the final p4 program, the table parametrized by
#   stateful_alus[i][j] is applied.
# num_state_groups:
#   type int, parametrizes the number of columns in salu_configs and stateful_alus.
# num_pipeline_stages:
#   type int, parametrizes the number of rows in stateless_alus.
# ignore_all_table_deps (I'll do it for you :-))
#   type string, a pragma line which will be inserted into the p4 program.
#
#
# Readme:
#   Everything is wrapped around in a single TofinoP4 object. To create a P4 program output,
#   first construct a TofinoP4 object, populate it accordingly, and call its render() method
#   for it to be written out to a .p4 program output with a supplied filename.

class TofinoP4(object):
    
    def _check_array_dim(self, a, d1, d2, name_a, name_d1, name_d2):
        err1 = name_a + ' is not populated'
        err2 = 'len(' + name_a + ') != ' + name_d1
        err3 = lambda x: 'len(' + name_a + '[' + x + ']' + ' != ' + name_d2
        errt = name_a + ' object is malformed or does not have array type'
        if a == None:
            raise Exception(err1)
        try:
            if len(a) != d1:
                raise Exception(err2)
            for i in range(len(a)):
                if len(a[i]) != d2:
                    raise Exception(err3(i))
        except:
            raise Exception(errt)


    def _check_fields(self, d, list_of_fields):
        if type(d) is not dict:
            raise Exception('type of object supplied to _check_fields(...) is not dict')
        for field in list_of_fields:
            if not (field in d):
                raise Exception('_check_fields(...): field ' + field + ' is not in dict\n') 


    def _check_stateful_alus_dim(self):
        self._check_array_dim(self.stateful_alus, 
                self.num_pipeline_stages, 
                self.num_state_groups, 
                'stateful_alus', 'num_pipeline_stages', 'num_state_groups')


    def _check_stateless_alus_dim(self):
        self._check_array_dim(self.stateless_alus, 
                self.num_pipeline_stages, 
                self.num_alus_per_stage, 
                'stateless_alus', 'num_pipeline_stages', 'num_alus_per_stage')


    def _check_salu_configs_dim(self):
        self._check_array_dim(self.salu_configs, 
                self.num_pipeline_stages, 
                self.num_state_groups, 
                'salu_configs', 'num_pipeline_stages', 'num_state_groups')


    def _produce_dummy_stateful_alu(self):
        return {
            'condition_lo_expr': 0,
            'condition_hi_expr': 0,
            'update_lo_1_predicate_expr': 0,
            'update_lo_1_value_expr': 0,
            'update_lo_2_predicate_expr': 0,
            'update_lo_2_value_expr': 0,
            'update_hi_1_predicate_expr': 0,
            'update_hi_1_value_expr': 0,
            'update_hi_2_predicate_expr': 0,
            'update_hi_2_value_expr': 0,
            'output_value_expr': 0,
            'output_dst': 'ipv4.pkt_0' }


    def _stateful_alus_wellformed(self):
        self._check_stateful_alus_dim()
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_state_groups):
                self._check_fields(self.stateful_alus[i][j], self.stateful_alu_fields)


    def _produce_dummy_stateless_alu(self):
        return {
                'enable': 0,
                'opcode': 0,
                'operand0': 0,
                'operand1': 0,
                'result': 0,
                'immediate_operand': 0 }

    def _stateless_alus_wellformed(self):
        self._check_stateless_alus_dim()
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_alus_per_stage):
                self._check_fields(self.stateless_alus[i][j], self.stateless_alu_fields)


    def _salu_configs_wellformed(self):
        self._check_salu_configs_dim()
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_state_groups):
                if self.salu_configs[i][j] != 0 and self.salu_configs[i][j] != 1:
                    raise Exception('salu_configs[' + str(i) + '][' + str(j) + '] is non-binary')


    def _generate_pragma_lines(self):
        lines = []
        for i in range(self.num_pipeline_stages):
            for j in range(self.num_state_groups):
                lines.append('@pragma ignore_table_dependency ' + self.sketch_name + '_stateful_alu_' + str(i) + '_' + str(j) + '_table')
        return "".join(lines)


    def __init__(self, sketch_name, num_alus_per_stage, num_state_groups, num_pipeline_stages, stateful_alus=None, stateless_alus=None, salu_configs=None):
        self.sketch_name = sketch_name 
        self.num_alus_per_stage = num_alus_per_stage
        self.num_state_groups = num_state_groups
        self.num_pipeline_stages = num_pipeline_stages
        self.stateful_alu_fields = ['condition_lo_expr', 'condition_hi_expr',
            'update_lo_1_predicate_expr',
            'update_lo_1_value_expr',
            'update_lo_2_predicate_expr',
            'update_lo_2_value_expr',
            'update_hi_1_predicate_expr',
            'update_hi_1_value_expr',
            'update_hi_2_predicate_expr',
            'update_hi_2_value_expr',
            'output_value_expr',
            'output_dst'
        ]
        self.stateless_alu_fields = ['enable', 'opcode', 'operand0', 'operand1', 'result', 'immediate_operand']

        print('TofinoP4 J2 template codegen: --------------------')
        print(stateful_alus)
        print(stateless_alus)
        print(salu_configs)
        print('num pipeline stages: ', num_pipeline_stages)
        print('num_state_groups: ', num_state_groups)
        print('num alus per stage: ', num_alus_per_stage)
        print('--------------------------------------------------')
        if stateful_alus == None:
            self.stateful_alus = [[self._produce_dummy_stateful_alu() for j in range(num_state_groups)] for i in range(num_pipeline_stages)]
        else:
            self.stateful_alus = stateful_alus 
        if stateless_alus == None:
            self.stateless_alus = [[self._produce_dummy_stateless_alu() for j in range(num_alus_per_stage)] for i in range(num_pipeline_stages)]
        else:
            self.stateless_alus = stateless_alus
        if salu_configs == None:
            self.salu_configs = [[0 for j in range(num_state_groups)] for i in range(num_pipeline_stages)]
        else:
            self.salu_configs = salu_configs
        self._stateful_alus_wellformed()
        self._stateless_alus_wellformed()
        self._salu_configs_wellformed()


    # set the (i,j)-th stateful alu object
    def set_stateful_alu(self, i, j, obj):
        if i < 0 or i >= self.num_pipeline_stages:
            raise Exception('variable i = ' + str(i) + ' index out of bounds')
        if j < 0 or j >= self.num_state_groups:
            raise Exception('variable j = ' + str(j) + ' index out of bounds')
        self._check_fields(obj, self.stateful_alu_fields)
        self.stateful_alus[i][j] = obj 


    # set the (i,j)-th stateless alu object
    def set_stateless_alu(self, i, j, obj):
        if i < 0 or i >= self.num_pipeline_stages:
            raise Exception('variable i = ' + str(i) + ' index out of bounds')
        if j < 0 or j >= self.num_alus_per_stage:
            raise Exception('variable j = ' + str(j) + ' index out of bounds')
        self._check_fields(obj, self.stateless_alu_fields)
        self.stateless_alus[i][j] = obj 


    # enable the (i,j)-th stateful alu 
    def enable_salu_config_at(self, i, j):
        if i < 0 or i >= self.num_pipeline_stages:
            raise Exception('variable i = ' + str(i) + ' index out of bounds')
        if j < 0 or j >= self.num_state_groups:
            raise Exception('variable j = ' + str(j) + ' index out of bounds')
        self.salu_configs[i][j] = 1

    # disable the (i,j)-th stateless alu
    def enable_salu_config_at(self, i, j):
        if i < 0 or i >= self.num_pipeline_stages:
            raise Exception('variable i = ' + str(i) + ' index out of bounds')
        if j < 0 or j >= self.num_state_groups:
            raise Exception('variable j = ' + str(j) + ' index out of bounds')
        self.salu_configs[i][j] = 0


    def _asdict(self):
        return { 'sketch_name': self.sketch_name,
                'num_pipeline_stages': self.num_pipeline_stages,
                'num_state_groups': self.num_state_groups,
                'num_alus_per_stage': self.num_alus_per_stage,
                'stateful_alus': self.stateful_alus,
                'stateless_alus': self.stateless_alus,
                'salu_configs': self.salu_configs,
                'ignore_all_table_deps': self._generate_pragma_lines() }


    # path: path under which the tofino_p4.j2 template is stored.
    # filename: essentially just tofino_p4.j2
    def render(self, path, filename): 
        fsloader=jinja2.FileSystemLoader(os.path.join(path))
        env = jinja2.Environment(loader=fsloader)
        tof = env.get_template(filename)
        return tof.render(self._asdict())

# reads in a TofinoP4 object from a json file
def tofinop4_from_json(path_to_json_file):
    with open(path_to_json_file) as fd:
        j=json.load(fd)
    return TofinoP4(j['sketch_name'], j['num_alus_per_stage'], j['num_state_groups'], j['num_pipeline_stages'], j['stateful_alus'], j['stateless_alus'], j['salu_configs'])

# reconstructs a TofinoP4 object from a GraphViz file
def tofinop4_from_graphviz(path_to_dot_file):
    pass

#t=TofinoP4('test_sketch',3,3,3)
#print(t.render('./','tofino_p4.j2'))
