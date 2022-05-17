import sys
import argparse
import re

import parser
from parser.asm import Assembly

LANGUAGE_NAME = 'XYZ'

#LINE_PARSE_REGEX = r'(.*\\\s*\n)*.*\n?'

def compile(lines):
    '''
    assembly = Assembly('testcompile')
    for line in lines:
        call = parser.analyze_line(line)
        if call is not None:
            assembly.add_function_call('start', call[0], call[1])

    return assembly.generate()
    '''
    #scope = parser.Scope('_main', lines)
    #print("Scopes:", scope.generate_code())

    asm = Assembly('test')
    scope = parser.Scope('_main', lines)
    asm.add_scope(scope)
    return asm.generate()


def load_file(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            data = file.read()
            lines = data.split('\n')
            return lines

    except FileNotFoundError:
        print("File", file_name, "not found!")

def main():
    parser = argparse.ArgumentParser(description=LANGUAGE_NAME + " language compiler.")
    parser.add_argument('file', metavar='F', type=str, help='Selects the file') #nargs can be '+' later for unlimited files
    parser.add_argument('--output', metavar='o', type=str, default='a.out', help="Output")
    args = parser.parse_args()

    lines = load_file(args.file)
    compiled = compile(lines)
    print(compiled)


if __name__ == '__main__':
    main()
