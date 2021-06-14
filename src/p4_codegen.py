
import ILP_Gurobi
import populate_j2
from ply import lex # for parsing PHV vars in stateful ALUs
import lexerRules
import re
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
        self._allocate_phv_container_struct_fields()
        self._postprocess_phv_container_fields()
        self.generate_stateless_alu_matrix()
        self.generate_stateful_alu_matrix_and_config()
        print('salu_configs: ', self.salu_configs_matrix)
        self.tofinop4 = populate_j2.TofinoP4(sketch_name, self.num_alus_per_stage, \
            self.num_state_groups, self.num_pipeline_stages, self.stateful_alus_matrix, \
                self.stateless_alus_matrix, self.salu_configs_matrix, self.packet_fields)


    def _postprocess_phv_container_fields(self):
        for alu in self.table_info.alus:
            if alu.get_type() == 'STATELESS':
                # Perform substitution to add the ipv4.* prefix into variables.
                alu.set_inputs(list(map(lambda x: 'ipv4.' + x if x in self.packet_fields else x, alu.inputs)))
                alu.set_output('ipv4.' + alu.output if alu.output in self.packet_fields else alu.output)
            if alu.get_type() == 'STATEFUL':
                pass # done in _allocate_phv_container_struct_fields already
    

    def _allocate_phv_container_struct_fields(self):
        self.packet_fields = set()
        lexer = lex.lex(module=lexerRules)
        for alu in self.table_info.alus:
            if alu.get_type() == 'STATELESS':
                # XXX: We use the lexer (again!) on the input and output fields
                # to each stateless ALU in order to see whether input/outputs
                # are indeed valid IDs (they can also be immediates, which are NUMBERs).
                # This might consume a bit more resources, but is cleaner than regexing manually.

                for input in alu.inputs + [alu.output]:
                    lexer.input(input)
                    toks = [tok for tok in lexer]
                    if toks[0].type == 'ID':
                        self.packet_fields.add(input)

            if alu.get_type() == 'STATEFUL':
                # XXX: here we need to parse out the rhs of each stateful ALU field
                # and see if it uses a variable that isn't the lhs of the ALU field.
                # this is rather clumsey to do, since the RHS currently is a string that
                # needs to be re-lexed although we have already lexed it again and again
                # in sketch_output_processor.py. 
                # However, there's not really a better alternative, since the relational
                # expressions (i.e. in condition_lo and condition_hi, correspondingly)
                # might also contain PHV vars.
                for lhs in alu.var_expressions:
                    rhs = alu.var_expressions[lhs]
                    lexer.input(rhs)
                    toks = []
                    for tok in lexer:
                        # look at each ID-type. Does it belong in the PHV container?
                        if tok.type == 'ID':
                            # If the variable name is not one of the stateful ALU blackbox built-ins,
                            # AND it is not register_lo or register_hi (see our comment in the SALU class;
                            # now we treat register_lo and register_hi as a keyword), we conclude that 
                            # it must be a packet field in the Domino program, and assign it to a PHV container
                            # struct field in the generated P4 program.
                            if (not (alu.demangle(tok.value)) in alu.var_expressions) \
                                and (alu.demangle(tok.value) != 'register_lo' and alu.demangle(tok.value) != 'register_hi'): 
                                # if the token is an ID and its ID name is not
                                # one of the SALU vars, we conclude that it must be
                                # a packet field that belongs in the PHV container.
                                print('p4_codegen: PHV var found for stateful ALU, it is ', tok.value)
                                self.packet_fields.add(tok.value)
                                tok.value = 'ipv4.' + tok.value
                        toks.append(tok)
                    alu.var_expressions[lhs] = ''.join(list(map(lambda x: x.value, toks)))
                

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
            'opcode': int(alu.opcode), # jinja template tests equality using int comparisons
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
            for alu, alu_id in self.stateless_alus:
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

    def generate_p4_output(self, filename, p4outputname):
        print('----------------------------------------------------')
        p4program = (self.tofinop4.render('./', filename))
        print(p4program)
        with open(p4outputname, 'w+') as fd:
            fd.writelines([p4program])