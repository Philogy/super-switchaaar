from .utils import indent


def wrap_as_macro(name_def, body, takes=0, returns=0, indent_lvl=2):
    if isinstance(body, list):
        body = '\n'.join(body)
    return f'''
#define macro {name_def} = takes({takes}) returns({returns}) {{
{indent(body, indent_lvl)}
}}'''


def pad_code(n):
    return ' '.join(['stop'] * n)
