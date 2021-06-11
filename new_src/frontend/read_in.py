from .. import pass_manager
from overrides import overrides

class ReadInFile(pass_manager.Pass):
    def __init__(self, file_name, pm : pass_manager.PassManager):
        super().__init__('ReadInFile', [], pm)
        self.file_name = file_name 
        pm.register(self)

    @overrides
    def run(self, _):
        with open(self.file_name) as fd:
            self.file_content = fd.readlines()

    @overrides
    def get_output(self):
        return self.file_content