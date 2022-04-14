from typing import Generic

from overrides import overrides
import ILP_Gurobi 

from backend import GenericCodegen
from template import GenericTemplate
class JsonTemplate(GenericTemplate):
    # def __init__(self, num_pipeline_stages, num_state_groups, num_alus_per_stage, stateful_alus, stateless_alus):
    def __init__(self, num_pipeline_stages, alu_dependencies, stateful_alus, stateless_alus):
        self.d = {
            "num_pipeline_stages" : num_pipeline_stages,
            "alu_dependencies": alu_dependencies,
            # "num_state_groups" : num_state_groups,
            # "num_alus_per_stage" : num_alus_per_stage,
            "stateful_alus" : stateful_alus,
            "stateless_alus" : stateless_alus,
        }
        print(self.d)

    def register(self, key, v):
        self.d[key] = v

    @overrides
    def get_dict(self):
        return self.d


class DominoCodegen(GenericCodegen):
    def __init__(self, table_info : ILP_Gurobi.ILP_TableInfo, ilp_output : ILP_Gurobi.ILP_Output, sketch_name, rename_packet_fields = False):
        self.table_info = table_info 
        self.ilp_output = ilp_output
        self.sketch_name = sketch_name 
        ilp_output.compute_alus_per_stage()
        self.num_pipeline_stages = ilp_output.num_stages
        self._process_alus()
        # self.generate_stateless_alu_matrix()
        # self.generate_stateful_alu_matrix_and_config()
        self.generate_stateless_alu_list()
        self.generate_stateful_alu_list()
        # self.template = JsonTemplate(self.num_pipeline_stages, self.num_state_groups,
        self.template = JsonTemplate(self.num_pipeline_stages, self.table_info.get_dependency_list(), self.stateful_alus_list, self.stateless_alus_list)

    def stateless_alu_descr(self, alu):
        assert alu.get_type() == "STATELESS"
        return {
            'id': alu.id,
            'opcode': int(alu.opcode), # jinja template tests equality using int comparisons
            'operand0': alu.inputs[0],
            'operand1': alu.inputs[1],
            'result': alu.output,
            'immediate_operand': alu.inputs[2]
        }

    @overrides
    def stateless_alu_to_dict(self, alu, stage):
        assert alu.get_type() == "STATELESS"
        return {
            'enable': 1 if alu.get_attribute("stage_status")[stage] else 0,
            'opcode': int(alu.opcode), # jinja template tests equality using int comparisons
            'operand0': alu.inputs[0],
            'operand1': alu.inputs[1],
            'result': alu.output,
            'immediate_operand': alu.inputs[2]
        }

    def stateful_alu_descr(self, salu):
        return salu.make_dict()
    
    @overrides
    def stateful_alu_to_dict_config_pair(self, salu, stage):
        return salu.make_dict(), salu.get_attribute('stage_status')[stage]