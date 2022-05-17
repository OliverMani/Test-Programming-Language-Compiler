VALID_WHITESPACE_CHARS = ' \t'
REGULAR_EXPRESSIONS = {
    'func_call': r'^\s*(?P<name>[a-zA-Z_]\w*)\s*\((?P<args>.*)\)\s*$',
    'compiler_msg': r'\s*\$(\S*)\s+(.*)',
    'condition_statement': r'^(if|while|dowhile|assert)\s*(.+)\s*(==)\s*(.+):\s*$',
    'func_create': r'^fun\s+([a-zA-Z_]\w*)\s*\((.*)\)\s*:\s*$',
    'var_mod': r'^([A-Za-z_]\w*)\s*(=|!=|\+=|\-=|\*=|\/=|\/\/=)\s*(.*)$', # variable modification, also creation
}

import math
from parser.asm import systemcheck as scheck
from parser import scope, caller, variable
import parser

"""
    A class to generate assembly code out of each scope
"""
class ScopeAssembly:
    def __init__(self, name, base_scope):
        self.name = name
        self.section_data = []
        self.section_text = {}
        self.section_bss  = []
        self.base_scope = base_scope
        self.variables_data = {}
        self.prepare_generation()

    def is_public(self):
        return self.base_scope.is_public

    def is_string(self, val):
        return (val.startswith('"') and val.endswith('"')) or (val.startswith('\'') and val.startswith('\''))

    def get_free_offset(self):
        addr = 0
        for var in self.variables_data.values():
            addr += var.blocksize
        return addr

    def prepare_generation(self):
        self.add_instruction(self.name, 'pushq %rbp')
        self.add_instruction(self.name, 'movq %rsp, %rbp')
        lines = self.base_scope.lines
        for line in lines:
            analyzed = parser.analyze_line(line)
            if not analyzed:
                continue
            if analyzed[0] == 'compiler_msg':
                name = analyzed[1]
                args = analyzed[2:][0]
                if name == 'syscall':
                    self.make_syscall(self.name, args[0], args[1:], push=False)
            if analyzed[0] == 'func_call':
                pass
            elif analyzed[0] == 'condition_statement':
                pass
            elif analyzed[0] == 'var_mod':
                #print(f"(VAR MOD {analyzed[1]}: {analyzed[3]})")
                if analyzed[1] not in self.variables_data: #if the variable is not defined before!
                    if analyzed[2] != '=':
                        continue # TODO: Raise Error here! Uninitialized variable!
                    self.put_var(analyzed[1], analyzed[3])
                else:
                    self.mod_var(analyzed[1], analyzed[3])


        self.add_instruction(self.name, 'popq %rbp')
        # tell how much space we need for variables/pointers in memory BEFORE running code
        self.section_text[self.name].insert(2, f'subq ${self.get_free_offset()+8}, %rsp')

    def get_var(self, name):
        return self.variables_data.get(name)

    def mod_var(self, name, value):

        var = self.get_var(name)
        address = var.address
        svalue = None
        if value.isdigit():
            svalue = f'${value}'
        elif self.is_string(value):
            svalue = self.create_constant('asciz', value)
        else:
            svalue = var
            if not svalue:
                return None
            ptr = variable.Pointer(name, svalue, address)
            ptr_addr = ptr.get_pointer_address()
            self.add_instruction(self.name, f'movq %rbp, %rax')
            if ptr_addr != 0:
                self.add_instruction(self.name, f'subq ${ptr_addr}, %rax')
            self.add_instruction(self.name, f'movq %rax, -{address}(%rbp)')

            #self.add_instruction(self.name, f'addq %rbp')
            return name


        self.add_instruction(self.name, f'movq {svalue}@GOTPCREL(%rip), %rax')
        self.add_instruction(self.name, f'movq %rax, -{var.address}(%rbp)')
        return name

    def put_var(self, name, value):
        address = self.get_free_offset()
        var = None
        if type(value) == variable.Variable or type(value) == variable.Pointer:
            var = variable.Pointer(name, value, address)
        else:
            var = variable.Variable(name, value, 8, address)
        self.variables_data[name] = var
        return self.mod_var(name, value)

    def guess_type(self, arg):
        if self.is_string(arg):
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

    """
        Works only for 64-bit softwares, push=False would be faster
        TO-DO: 32-bit support
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
                else: # if it is string (make pointer)
                    #print(f"SYSCALL ASCIZ {str(args[i])}")
                    #print(f"IS STRING: {self.is_string(args[i])}")
                    if self.is_string(args[i]):
                        constant_name = self.create_constant('asciz', f'{str(args[i])}')
                        if constant_name:
                            self.add_instruction(scopename, f'movq {constant_name}@GOTPCREL(%rip), %{registers_to_use[i]}')
                    else: # this is a variable
                        var = self.get_var(args[i])
                        self.add_instruction(scopename, f'movq -{var.address}(%rbp), %{registers_to_use[i]}')
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


    def add_instruction(self, scopename, line):
        if scopename not in self.section_text:
            self.section_text[scopename] = []
        self.section_text[scopename].append(line)

    def create_constant(self, type, value, name=None):
        if not name:
            name = f'.CD_{len(self.section_data)}'
         #if type(value) == list or type(value) == tuple:
         #    value = ', '.join(value)
        if value is not None:
            self.section_data.append(f'{name}: .{type} {value}')
            return name

    def add_function_call(self, scopename, funcname, args):
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


class Scope:
    def __init__(self, name, lines, public=True, parent=None):
        self.name = name
        self.lines = []
        self.parent_scope = parent # we can use for variables
        self.subscopes = {}
        self.variables = {}
        self.is_public = public

        if lines: # parse lines
            i = 0
            while i < len(lines):
                line = lines[i]
                if line and line[0] in VALID_WHITESPACE_CHARS:

                    subscope_lines = []

                    while i < len(lines) and (not lines[i] or lines[i][0] in VALID_WHITESPACE_CHARS):
                        if lines[i]:
                            subscope_lines.append(lines[i][1:])
                        i += 1
                    subscope = self.add_anonymous_scope(subscope_lines)
                    self.lines.append(subscope)
                else:
                    self.lines.append(line)
                    i += 1

    def find_variable(self, name):
        if name in self.variables:
            return self.variables[name]
        elif self.parent_scope is not None:
            return self.parent_scope.find_variable(name)
        return None

    def generate_code(self):
        s = f'_{self.name}:\n'
        for line in self.lines:
            if type(line) == Scope:
                s += f'REFERENCE SCOPE {line.name}\n'
            elif type(line) == str:
                s += line + '\n'

        for scope in self.subscopes.values():
            s += f'\n\n'
            s += scope.generate_code()
        return s


    def add_anonymous_scope(self, lines):
        name = f'.S_{len(self.subscopes)}'
        scope = Scope(name, lines, public=False)
        self.subscopes[name] = scope
        return scope

    def add_line(self, line):
        self.lines.append(line)
