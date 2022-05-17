import math
from parser.asm import systemcheck as scheck

class Assembly:
    def __init__(self, name):
        self.name = name
        self.section_data = []
        self.section_text = {}
        self.section_bss  = []

    def guess_type(self, arg):
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith('\'') and arg.startswith('\'')):
            return 'asciz'
        elif arg.isdigit():
            n = int(arg)
            if n < 2**8:
                return 'byte' # byte/char
            elif n < 2**16:
                return 'short' # short
            elif n < 2**32:
                return 'int' # int
            elif n < 2**64:
                return 'quad' # long
            elif n < 2**128:
                return 'octa' # 128-bit integer


    def create_constant(self, type, value):
        name = f'.CD_{len(self.section_data)}'
        #if type(value) == list or type(value) == tuple:
        #    value = ', '.join(value)
        if value is not None:
            self.section_data.append(f'{name}: .{type} {value}')
            return name

    def add_instruction(self, scopename, line):
        if scopename not in self.section_text:
            self.section_text[scopename] = []
        self.section_text[scopename].append(line)

    """
        Works only for 64-bit softwares, push=False would be faster
    """
    def make_syscall(self, scopename, ax, args, push=True):
        if scopename and ax and args:
            registers_to_use = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
            registers_to_push = min(len(args), len(registers_to_use))
            # If push registers, push the arguments registers
            if push:
                for i in range(registers_to_push):
                    self.add_instruction(scopename, f'pushq %{registers_to_use[i]}')

            # MOVe to registers
            for i in range(registers_to_push):
                # We need to check if the argument is an number or an pointer
                if type(args[i]) == int or (type(args[i]) == str and args[i].isdigit()): # if number
                    self.add_instruction(scopename, f'movq ${args[i]}, %{registers_to_use[i]}')
                else: # if it is pointer
                    constant_name = self.create_constant('asciz', f'"{str(args[i])}"')
                    if constant_name:
                        self.add_instruction(scopename, f'movq {constant_name}@GOTPCREL(%rip), %{registers_to_use[i]}')

            # PUSH if needed
            for i in range(len(args) - registers_to_push):
                # We need to check if the argument is an number or an pointer
                if type(args) == int or (type(args) == str and args.isdigit()):
                    self.add_instruction(scopename, f'pushq ${args[i]}')
                else:
                    constant_name = self.create_constant('asciz', f'"{str(args[i])}"')
                    if constant_name:
                        self.add_instruction(scopename, f'pushq {constant_name}')
            # call syscall itself
            self.add_instruction(scopename, f'movq ${ax}, %rax')
            self.add_instruction(scopename, 'syscall')
            # cleanup memory
            if len(args) - registers_to_push > 0:
                self.add_instruction(scopename, f'add ${(len(args) - registers_to_use) * 8}, %rsp')

            # If push registers, pop the arguments registers
            if push:
                for i in range(registers_to_push-1, -1, -1):
                    self.add_instruction(scopename, f'popq %{registers_to_use[i]}')


    def add_function_call(self, scopename, funcname, args):
        print("ADD FUNCTION CALL:", funcname, args)
        registers_to_use = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
        to_push = min(len(args), len(registers_to_use))

        # push if length of arguments is more than 6
        for i in range(to_push):
            self.add_instruction(scopename, f'pushq %{registers_to_use[i]}')

        args_to_pop = 0

        for i in range(len(args)):
            name = self.create_constant(self.guess_type(args[i]), args[i])
            if i < 6:
                self.add_instruction(scopename, f'mov {name}@GOTPCREL(%rip), %{registers_to_use[i]}')
            else:
                args_to_pop += 1
                self.add_instruction(scopename, f'pushq (%{name})')
        self.add_instruction(scopename, f'call {funcname}')

        if args_to_pop != 0:
            self.add_instruction(scopename, f'add {args_to_pop*8}', '%rsp')

        # pop if pushed for args
        for i in range(to_push-1, -1, -1):
            self.add_instruction(scopename, 'popq %' + registers_to_use[i])


    def generate(self):
        s = '.text\n'
        for scopename, scope in self.section_text.items():
            s += scopename + ':\n'
            for line in scope:
                s += '\t' + line + '\n'
        s += '.data\n'
        for line in self.section_data:
            s += line + '\n'
        s += '.bss\n'
        for line in self.section_bss:
            s += line + '\n'
        return s
