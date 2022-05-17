from sys import platform

"""
    Returns a hex string of the number for RAX register
"""
def convert_syscall_number_by_os(number, system = None):
    if system is None:
        system = platform
    if system == 'darwin':
        return hex(0x2000000 | int(number))
    return hex(number)
