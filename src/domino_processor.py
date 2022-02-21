
# TODO: implement
class DominoOutputProcessor(object):
    def __init__(self, comp_graph):
        self.comp_graph = comp_graph

    def postprocessing(self):
        print("Domino Postprocessing Unimplemented")
    
    def process_single_stateful_output(self, file, out):
        print('Domino Postprocessor: single stateful output from file ', file, ' out ', out)
    
    def process_stateless_output(self, file, out):
        print('Domino Postprocessor: single stateless output from file', file, ' out ', out)