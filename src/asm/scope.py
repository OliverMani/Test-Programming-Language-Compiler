import re
import caller
import variable
import errors

VALID_WHITESPACE_CHARS = ' \t'

FUNC_CALL = 'func_call'
COMPILER_MSG = 'compiler_msg'
CONDITION_STATEMENT = 'condition_statement'
FUNC_CREATE = 'func_create'
VAR_MOD = 'var_mod'
SCOPE = 'scope'

REGULAR_EXPRESSIONS = {
    FUNC_CALL: r'^\s*(?P<name>[a-zA-Z_]\w*)\s*\((?P<args>.*)\)\s*$',
    COMPILER_MSG: r'\s*\$(\S*)\s+(.*)',
    CONDITION_STATEMENT: r'^(if|while|dowhile|assert)\s*(.+)\s*(==|!=)\s*(.+):\s*$',
    FUNC_CREATE: r'^fun\s+([a-zA-Z_]\w*)\s*\((.*)\)\s*:\s*$',
    VAR_MOD: r'^([A-Za-z_]\w*)\s*(=|!=|\+=|\-=|\*=|\/=|\/\/=)\s*(.*)$', # variable modification, also creation
}

# Using regular expression to read the lines
def analyze_line(line):
    if type(line) == str:
        for key, expression in REGULAR_EXPRESSIONS.items():
            #print("LINE:", line)
            match = re.match(REGULAR_EXPRESSIONS[key], line)
            if match is not None:
                if key == FUNC_CALL:
                    name, args_str = match.groups()
                    parsed_args = caller.parse_func_call_args_str(args_str)
                    #print("Found function:", name, "with args:", parsed_args, f"(from {args_str})")
                    return (key, name, parsed_args)
                elif key == COMPILER_MSG:
                    name, args_str = match.groups()
                    parsed_args = caller.parse_func_call_args_str(args_str)
                    #print("Found syscall:", name, "with args:", parsed_args, f"(from {args_str})")
                    return (key, name, parsed_args)
                elif key == CONDITION_STATEMENT:
                    #print("Found statement")
                    statement, left, action, right = match.groups()
                    return (key, statement, left, action, right)
                elif key == VAR_MOD:
                    varname, action, value = match.groups()
                    return (key, varname, action, value)
    elif type(line) == ScopeAssembly:
        return (SCOPE, line)

class ScopeAssembly:
    def __init__(self, name, lines, parent=None, public=False, auto_prepare=True):
        self.name = name
        self.lines = []
        self.parent = parent
        self.public = public
        self.section_bss  = []
        self.section_data = []
        self.section_text = []
        self.variables_data = {}
        self.statement_count = 0

        self.subscopes = {}

        self.split_scopes(lines)
        if auto_prepare:
            self.prepare_generation()

    def get_statement_count(self):
        if self.parent is None:
            return self.statement_count
        return self.statement_count + parent.get_statement_count()

    def prepare_generation(self):
        self.add_instruction('pushq %rbp')
        condition_action = None
        for line in self.lines:
            analyzed = analyze_line(line)
            if analyzed:
                key = analyzed[0]
                if key is COMPILER_MSG:
                    call, args = analyzed[1:]
                    if call.lower() == 'syscall':
                        self.make_syscall(args[0], args[1:], push=False)
                elif key is FUNC_CALL:
                    pass
                elif key is CONDITION_STATEMENT:
                    statement, left, action, right = analyzed[1:]
                    left = left.replace(' ', '').replace('\t', '')
                    right = right.replace(' ', '').replace('\t', '')
                    statement_number = self.get_statement_count()
                    self.statement_count += 1
                    if statement in ['while', 'dowhile']:
                        self.add_instruction(f'.WS{statement_number}:') # "While Statement" jump point

                    if statement == 'if':
                        lvalue = None
                        rvalue = None
                        if self.is_string(left):
                            lvalue = self.create_constant('asciz', left)
                        elif left.isdigit():
                            lvalue = f'${left}'
                        else:
                            lvalue = f'-{self.get_var(left).address}(%rbp)'
                        #print("LEFT VAR:", self.variables_data[left], f"(Left: {left})")

                        if self.is_string(right):
                            rvalue = self.create_constant('asciz', right)
                        elif right.isdigit():
                            rvalue = f'${right}'
                        else:
                            rvalue = f'-{self.get_var(right)}(%rbp)'

                        self.add_instruction(f'cmpq {rvalue}, {lvalue}')
                        condition_action = 'jne' if action == '==' else 'je'





                elif key is FUNC_CREATE:
                    pass
                elif key is VAR_MOD:
                    varname, action, value = analyzed[1:]
                    var = self.get_var(varname)
                    if var:
                        self.mod_var(varname, value)
                    else:
                        self.put_var(varname, value)
                elif key is SCOPE:
                    scope = analyzed[1]
                    if condition_action is None or condition_action == 'ENDIF':
                        self.add_instruction(f'callq {scope.name}')
                    else:
                        endif_name = f'.ES{self.get_statement_count()}' # "End Statement"
                        self.add_instruction(f'{condition_action} {endif_name}')
                        self.add_instruction(f'callq {scope.name}')
                        self.add_instruction(f'{endif_name}:')
                        condition_action = 'ENDIF'
                    #print("SUBSCOPE:", scope)
        malloc = self.get_free_offset()
        if malloc != 0:
            self.section_text.insert(2, f'subq ${malloc}, %rsp')
            self.add_instruction(f'addq ${malloc}, %rsp')
        self.add_instruction('popq %rbp')
        self.add_instruction('retq')
        for subscope in self.subscopes.values():
            subscope.prepare_generation()

    def get_var(self, name):
        var = self.variables_data.get(name)

        if var is None and self.parent is not None:
            return self.parent.get_var(name)
        return var

    def get_free_offset(self):
        addr = 0
        for var in self.variables_data.values():
            addr += var.blocksize
        return addr

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
            self.add_instruction(f'movq %rbp, %rax')
            if ptr_addr != 0:
                self.add_instruction(f'subq ${ptr_addr}, %rax')
            self.add_instruction(f'movq %rax, -{address}(%rbp)')

            #self.add_instruction(self.name, f'addq %rbp')
            return name

        #print("SVALUE:", svalue)
        gotpcrel = '@GOTPCREL(%rip)' if not svalue.startswith('$') else ''
        self.add_instruction(f'movq {svalue}{gotpcrel}, %rax')
        self.add_instruction(f'movq %rax, -{var.address}(%rbp)')
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


    def split_scopes(self, lines):
        if lines:
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

    def add_anonymous_scope(self, lines):
        name = f'.S{len(self.subscopes)}'
        asm = ScopeAssembly(name, lines, parent=self, auto_prepare=False)
        self.subscopes[name] = asm
        return asm

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

    def create_constant(self, type, value, name=None):
        if not name:
            name = f'.CD_{len(self.section_data)}'
         #if type(value) == list or type(value) == tuple:
         #    value = ', '.join(value)
        if value is not None:
            self.section_data.append(f'{name}: .{type} {value}')
            return name


    def get_recursive_data(self):
        data = self.section_data
        for subscope in self.subscopes.values():
            data += subscope.get_recursive_data()
        return data

    def get_recursive_text(self):
        text = []
        for name, subscope in self.subscopes.items():
            text.append(f'{name}:')
            for _text in subscope.section_text:
                text.append('  ' + _text)
            text.append('')
        return text

    def get_recursive_bss(self):
        bss = self.section_bss
        for subscope in self.subscopes.values():
            bss += subscope.get_recursive_bss()
        return bss

    def recursive_extern_public(self):
        public_scopes = []
        if self.public:
            public_scopes.append(self.name)
        for subscope in self.subscopes.values():
            public_scopes += subscope.recursive_extern_public()
        return public_scopes

    def generate(self):
        s = '.data:\n'
        for data in self.get_recursive_data():
            s += f'{data}\n'
        s += '\n.bss:\n'
        for bss in self.get_recursive_bss():
            s += f'{bss}\n'
        s += '\n.text:\n'

        for scopename in self.recursive_extern_public():
            s += f'.globl {scopename}\n'


        s += '\n'.join(self.get_recursive_text())
        s += f'\n{self.name}:\n'
        s += '\n'.join(['  ' + line for line in self.section_text])
        return s

        #print('\n'.join(self.section_text))


    def add_instruction(self, instruction):
        self.section_text.append(instruction)

    def is_string(self, val):
        return (val.startswith('"') and val.endswith('"')) or (val.startswith('\'') and val.startswith('\''))

    # Maybe re-think this function, it's too fat and I think "pushing" is gonna cause overriding variables...
    def make_syscall(self, ax, args, push=True):
        if ax and args:
            registers_to_use = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']
            registers_to_push = min(len(args), len(registers_to_use))
            # If push registers, push the arguments registers
            if push:
                for i in range(registers_to_push):
                    self.add_instruction(f'pushq %{registers_to_use[i]}')

            # MOVe to registers
            for i in range(registers_to_push):
                # We need to check if the argument is an number or an pointer
                if type(args[i]) == int or (type(args[i]) == str and args[i].isdigit()): # if number
                    self.add_instruction(f'movq ${args[i]}, %{registers_to_use[i]}')
                else: # if it is string (make pointer)
                    #print(f"SYSCALL ASCIZ {str(args[i])}")
                    #print(f"IS STRING: {self.is_string(args[i])}")
                    if self.is_string(args[i]):
                        constant_name = self.create_constant('asciz', f'{str(args[i])}')
                        if constant_name:
                            self.add_instruction(f'movq {constant_name}@GOTPCREL(%rip), %{registers_to_use[i]}')
                    else: # this is a variable
                        var = self.get_var(args[i])
                        if not var:
                            raise errors._VariableNotFound(f'Variable \'{args[i]}\' could not be found!')
                        self.add_instruction(f'movq -{var.address}(%rbp), %{registers_to_use[i]}')
            # PUSH if needed
            for i in range(len(args) - registers_to_push):
                # We need to check if the argument is an number or an pointer
                if type(args) == int or (type(args) == str and args.isdigit()):
                    self.add_instruction(f'pushq ${args[i]}')
                else:
                    constant_name = self.create_constant('asciz', f'"{str(args[i])}"')
                    if constant_name:
                        self.add_instruction(f'pushq {constant_name}')
            # call syscall itself
            self.add_instruction(f'movq ${ax}, %rax')
            self.add_instruction('syscall')
            # cleanup memory
            if len(args) - registers_to_push > 0:
                self.add_instruction(f'add ${(len(args) - registers_to_use) * 8}, %rsp')

            # If push registers, pop the arguments registers
            if push:
                for i in range(registers_to_push-1, -1, -1):
                    self.add_instruction(f'popq %{registers_to_use[i]}')
