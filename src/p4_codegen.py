
import ILP_Gurobi
import populate_j2

class P4Codegen(object):



    def __init__(self, table_info : ILP_Gurobi.ILP_TableInfo, ilp_output : ILP_Gurobi.ILP_Output, sketch_name):
        #sketch_name, num_alus_per_stage, num_state_groups, num_pipeline_stages, stateful_alus=None, stateless_alus=None, salu_configs=None
        self.sketch_name = sketch_name 
        self.table_info = table_info
        self.ilp_output = ilp_output 
        ilp_output.compute_alus_per_stage()
        self.num_pipeline_stages = ilp_output.num_stages 

        print('================P4Codegen')
        print(self.table_info.alus)
        self._process_alus()
        self.generate_stateless_alu_matrix()
        self.generate_stateful_alu_matrix_and_config()
        print('salu_configs: ', self.salu_configs_matrix)
        self.tofinop4 = populate_j2.TofinoP4(sketch_name, self.num_alus_per_stage, \
            self.num_state_groups, self.num_pipeline_stages, self.stateful_alus_matrix, \
                self.stateless_alus_matrix, self.salu_configs_matrix)

    def _process_alus(self):
        self.stateless_alus = []
        self.stateful_alus = []
        stateless_id = 0
        stateful_id = 0
        for alu in self.table_info.alus:
            alu.set_attribute("stage_status", [False for i in range(self.num_pipeline_stages)])
            if alu.get_type() == 'STATELESS':
                alu.set_attribute("stateless_id", stateless_id)
                self.stateless_alus.append((alu, stateless_id))
                stateless_id += 1
            elif alu.get_type() == 'STATEFUL':
                alu.set_attribute("stateful_id", stateful_id)
                self.stateful_alus.append((alu, stateful_id))
                stateful_id += 1
            else:
                raise Exception("P4Codegen: _process_alus: error: invalid alu type: " + alu.get_type())
        self.num_state_groups = stateful_id 
        self.num_alus_per_stage = stateless_id 

    def stateless_alu_to_dict(self, alu, stage):
        assert alu.get_type() == "STATELESS"
        return {
            'enable': 1 if alu.get_attribute("stage_status") else 0,
            'opcode': alu.opcode,
            'operand0': alu.inputs[0],
            'operand1': alu.inputs[1],
            'result': alu.output,
            'immediate_operand': alu.inputs[2]
        }

    def stateful_alu_to_dict_config_pair(self, salu, stage):
        assert salu.get_type() == "STATEFUL"
        return salu.var_expressions, salu.get_attribute('stage_status')


    def generate_stateless_alu_matrix(self):
        self.stateless_alus_matrix = []
        for stage in range(self.num_pipeline_stages):
            curr_stage = []
            for alu in self.stateless_alus:
                curr_stage.append(self.stateless_alu_to_dict(alu, stage))
            self.stateless_alus_matrix.append(curr_stage)

    def generate_stateful_alu_matrix_and_config(self):
        self.salu_configs_matrix = []
        self.stateful_alus_matrix = []
        print('* generating stateful ALU matrix. num pipeline stages: ', self.num_pipeline_stages)
        for stage in range(self.num_pipeline_stages):
            curr_stage = []
            curr_stage_configs = []
            print(' - curr_stage: ', stage)
            for salu, alu_id in self.stateful_alus:
                print(' -* this SALU: ', salu )
                salu_dict, enabled = self.stateful_alu_to_dict_config_pair(salu, stage)
                curr_stage.append(salu_dict)
                curr_stage_configs.append(1 if enabled else 0)
            self.salu_configs_matrix.append(curr_stage_configs)
            self.stateful_alus_matrix.append(curr_stage)

    def generate_p4_output(self, filename):
        print('----------------------------------------------------')
        print(self.tofinop4.render('./', filename))