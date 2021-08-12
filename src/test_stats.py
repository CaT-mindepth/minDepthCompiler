
import time
# 
# utility for collecting statistics during benchmark rounds
# The statistics for each Domino program can be wrapped in
# a Statistics object, which is then passed into everything
# to collect data.
# currently we keep track
#     - Num pairs of successful merges 
#     - Time spent during merging
#     - Number of ALUs per stage
class Statistics(object):
    def __init__(self, test_name, fd):
        self.test_name = test_name
        self.start_time = time.time()
        self.num_successful_merges = 0
        self.merging_done = False
        self.synthesis_done = False
        self.ilp_done = False
        self.fd = fd
        self.synthesis_comp_start_times = {}
        self.synthesis_comp_end_times = {}

    def start_merging(self):
        self.merging_start_time = time.time()
    
    def end_merging(self):
        self.merging_end_time = time.time()
        self.merging_time = self.merging_end_time - self.merging_start_time
        self.merging_done = True

    def update_num_components(self, num_components):
        self.num_components = num_components

    def incr_num_successful_merges(self):
        self.num_successful_merges += 1

    def update_num_postmerge_components(self, num_postmerge_components):
        self.num_postmerge_components = num_postmerge_components

    def update_num_alus_per_stage(self, num_alus_per_stage):
        self.num_alus_per_stage = num_alus_per_stage
    
    def update_num_stages(self, num_stages):
        self.num_stages = num_stages

    def update_num_alus(self, num_alus):
        self.num_alus = num_alus
    
    def update_num_stateful_alus(self, num_stateful_alus):
        self.num_stateful_alus = num_stateful_alus
    
    def update_num_stateless_alus(self, num_stateless_alus):
        self.num_stateless_alus = num_stateless_alus
    
    def start_synthesis(self):
        self.synthesis_start_time = time.time()
    
    def start_synthesis_comp(self, comp_name):
        self.synthesis_comp_start_times[comp_name] = time.time()

    def end_synthesis_comp(self, comp_name):
        self.synthesis_comp_end_times[comp_name] = time.time()

    def end_synthesis(self):
        self.synthesis_end_time = time.time()
        self.synthesis_time = self.synthesis_end_time - self.synthesis_start_time
        self.synthesis_done = True
    
    def start_ilp(self):
        self.ilp_start_time = time.time()
    
    def end_ilp(self):
        self.ilp_end_time = time.time()
        self.ilp_time = self.ilp_end_time - self.ilp_start_time
        self.ilp_done = True

    def end(self):
        self.end_time = time.time()
        self.overall_time = self.end_time - self.start_time
    
    def report(self):
        self.fd.write('---------------------------- finished testing ' + self.test_name + '; statistics  ---------------------\n')
        if self.merging_done:
            self.fd.write("Time taken during merging: {} s\n".format(self.merging_time))
        if self.synthesis_done:
            self.fd.write("Time taken during synthesis: {} s\n".format(self.synthesis_time))
            for comp_name in self.synthesis_comp_start_times:
                self.fd.write("Component " + comp_name + " : " + ("{} s\n".format(self.synthesis_comp_end_times[comp_name] - self.synthesis_comp_start_times[comp_name])))
        if self.ilp_done:
            self.fd.write("Time taken during ILP: {} s\n".format(self.ilp_time))
        self.fd.write("Time taken overall: {} s\n".format(self.overall_time))
        self.fd.write('Num ALU stages: ' + str(self.num_stages) + '\n')
        self.fd.write('\nNum ALUs: ' + str(self.num_alus))
        self.fd.write('\nNum stateful ALUs: ' + str(self.num_stateful_alus))
        self.fd.write('\nNum stateless ALUs: '+ str(self.num_stateless_alus))
        self.fd.write('\nNum stages: ' + str(self.num_stages))
        self.fd.write('\nNum ALUs per stage: ' + str(self.num_alus_per_stage))
        self.fd.write('\nNumber of components pre-merge: ' + str(self.num_components))
        self.fd.write('\nNumber of successful merges: ' + str(self.num_successful_merges))
        self.fd.write('\nNumber of components post-merge: ' + str(self.num_postmerge_components))
        self.fd.write('\n------------------------------------------------------------------------------------------------\n')
