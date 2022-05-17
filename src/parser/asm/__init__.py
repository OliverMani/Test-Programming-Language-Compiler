import math
from parser import scope
from parser.asm import scope as asmscope



class Assembly:
    def __init__(self, name):
        self.name = name
        self.scopes = []

    def generate(self):
        section_bss  = []
        section_data = []
        section_text = {}

        public_scopes = []

        for scope in self.scopes: # section_data
            for data in scope.section_data:
                section_data.append(data)

        for scope in self.scopes: # section_text
            if scope.name not in section_text:
                section_text[scope.name] = []
            if scope.is_public():
                public_scopes.append(scope.name)
            for line in scope.section_text:
                section_text[scope.name].append('\n'.join(['  ' + item for item in scope.section_text[scope.name]] + ['  ret']))

        for scope in self.scopes: #section_bss
            pass

        s = '.text\n'
        for scopename in public_scopes:
            s += f'.globl {scopename}\n'
        s += '\n'

        for scopename, text in section_text.items():
            s += f'{scopename}:\n'
            
            for line in text:
                s += f'{line}\n'
        s += '\n.data\n'
        for data in section_data:
            s += f'{data}\n'
        return s

    def add_scope(self, base_scope):
        if type(base_scope) == scope.Scope:
            base_scope = asmscope.ScopeAssembly(base_scope.name, base_scope)
        self.scopes.append(base_scope)
