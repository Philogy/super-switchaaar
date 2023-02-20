from eth_utils import function_signature_to_4byte_selector


def sig_to_selector(sig: str) -> int:
    return int.from_bytes(function_signature_to_4byte_selector(sig), 'big')


def indent(code: str, size=2) -> str:
    indent = ' ' * size
    return indent + code.replace('\n', f'\n{indent}')
