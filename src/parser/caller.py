
def args_split(str):
    _split = []
    last_quote = None
    backslash_mode = False
    s = ''

    for ch in str:
        if ch == '\\':
            backslash_mode = True
            s += ch
            continue
        if not last_quote and ch in ' \t':
            continue
        elif ch == '\'' or ch == '"':
            if last_quote is None:
                last_quote = ch
            elif not backslash_mode and ch == last_quote:
                last_quote = None
            #else:
            #    s += ch
            s += ch
        elif ch == ',' and last_quote is None:
            if s.isdigit():
                s = int(s)
            _split.append(s)
            s = ''
        else:
            s += ch

        backslash_mode = False
    if s.isdigit():
        s = int(s)
    _split.append(s)
    return _split


def parse_func_def_args_str(str):
    pass

def parse_func_call_args_str(str):
    args = args_split(str)
    return args
