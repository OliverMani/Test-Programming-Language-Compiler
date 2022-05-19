from sys import argv
from asm.scope import ScopeAssembly
import errors

def load_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read().split('\n')
    except FileNotFoundError:
        print("File not found!")

def main(args):
    if len(args) == 0:
        print("Please select a file!")
    else:
        lines = load_file(args[0])
        if lines:
            try:
                asm = ScopeAssembly('_main', lines, public=True)

                code = asm.generate()
                print(code)
            except errors.CompileError as e:
                e.filename = args[0]
                e.display()

if __name__ == '__main__':
    main(argv[1:])
