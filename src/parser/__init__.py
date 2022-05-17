# parseline

import re
import parser.caller
from parser.scope import Scope, REGULAR_EXPRESSIONS

# Using regular expression to read the lines
def analyze_line(line):
    for key, expression in REGULAR_EXPRESSIONS.items():
        match = re.match(REGULAR_EXPRESSIONS[key], line)
        if match is not None:
            if key == 'func_call':
                name, args_str = match.groups()
                parsed_args = caller.parse_func_call_args_str(args_str)
                #print("Found function:", name, "with args:", parsed_args, f"(from {args_str})")
                return (key, name, parsed_args)
            elif key == 'compiler_msg':
                name, args_str = match.groups()
                parsed_args = caller.parse_func_call_args_str(args_str)
                #print("Found syscall:", name, "with args:", parsed_args, f"(from {args_str})")
                return (key, name, parsed_args)
            elif key == 'condition_statement':
                #print("Found statement")
                statement, left, action, right = match.groups()
                return (key, statement, left, action, right)
            elif key == 'var_mod':
                varname, action, value = match.groups()
                return (key, varname, action, value)
