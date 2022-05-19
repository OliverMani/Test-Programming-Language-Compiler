from colors import TextColor
import sys

class CompileError(Exception):
    def __init__(self, message, line=None, line_number=None, filename=None):
        super().__init__(self, message)
        self.message = message
        self.line = line
        self.line_number = line_number
        self.filename = filename

    def display(self):
        print(f"{TextColor.RED}{TextColor.BOLD}Error:{TextColor.END} {self.message}", file=sys.stderr)
        print(f"{TextColor.LIGHT_WHITE}{TextColor.BOLD}{self.filename}:{self.line_number}{TextColor.END}", file=sys.stderr)
        print(f"{self.line}")
        print()


class _VariableNotFound(CompileError):
    pass

class _InvalidOperation(CompileError):
    pass

def display_error(error, line):
    print("Error...")
