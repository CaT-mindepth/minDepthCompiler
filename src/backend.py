import lexerRules
from ply import lex 

class GenericCodegen(object):

    def _process_alus(self):
        self.stateless_alus = []
        self.stateful_alus = []
        stateless_id = 0
        stateful_id = 0
        for alu in self.table_info.alus:
            # TODO: problem: stage_status was never set!!!
            stages_vec = [False for i in range(self.num_pipeline_stages)]
            stages_vec[self.ilp_output.get_alu_stage(0, alu.id)] = True
            print('alu ', alu.id, ' is of type ', alu.get_type(), '; scheduled to stage ', self.ilp_output.get_alu_stage(0, alu.id))
            alu.set_attribute("stage_status", stages_vec)
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
        print('Codegen processed ALUs: ', len(self.stateless_alus), ' ; ', self.stateless_alus)
        print('Codegen processed SALUs: ', len(self.stateful_alus), ' ; ', self.stateful_alus)

    def stateless_alu_to_dict(self, alu, stage):
        pass


    def stateful_alu_to_dict_config_pair(self, salu, stage):
        pass

    def generate_stateless_alu_list(self):
        self.stateless_alus_list = []
        for alu, alu_id in self.stateless_alus:
            alu_dict = self.stateless_alu_descr(alu)
            self.stateless_alus_list.append(alu_dict)
    
    def generate_stateful_alu_list(self):
        self.stateful_alus_list = []
        for salu, alu_id in self.stateful_alus:
            salu_dict = self.stateful_alu_descr(salu)
            self.stateful_alus_list.append(salu_dict)
    

    def generate_stateless_alu_matrix(self):
        self.stateless_alus_matrix = []
        for stage in range(self.num_pipeline_stages):
            curr_stage = []
            for alu, alu_id in self.stateless_alus:
                curr_stage.append(self.stateless_alu_to_dict(alu, stage))
            print('generate_stateless_alu_matrix: stage ', stage, ', with ALUs ', curr_stage)
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
                if salu == None:
                    raise Exception("wtf!")
                print(' -* this SALU: ', salu )
                salu_dict, enabled = self.stateful_alu_to_dict_config_pair(salu, stage)
                curr_stage.append(salu_dict)
                curr_stage_configs.append(1 if enabled else 0)
            self.salu_configs_matrix.append(curr_stage_configs)
            self.stateful_alus_matrix.append(curr_stage)

    def generate_p4_output(self, filename, p4outputname):
        print('----------------------------------------------------')
        p4program = (self.template.render('./', filename))
        print(p4program)
        with open(p4outputname, 'w+') as fd:
            fd.writelines([p4program])

    def generate_json_output(self, filename, p4outputname):
        import json
        print('----------------------------------------------------')
        output_dict = self.template.get_dict()
        print(output_dict)
        with open(p4outputname, 'w+') as fd:
            fd.writelines(json.dumps(output_dict))
    