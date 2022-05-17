class Variable:
    def __init__(self, name, data, blocksize, address):
        self.name = name
        self.data = data
        self.blocksize = blocksize
        self.address = address

class Pointer(Variable):
    def __init__(self, name, var, stack_offset):
        super().__init__(name, var, 8, stack_offset)
        self.var = var

    def get_pointer_address(self):
        return self.var.address
