from eth_utils import function_signature_to_4byte_selector


def sig_to_selector(sig: str) -> int:
    return int.from_bytes(function_signature_to_4byte_selector(sig), 'big')


def indent(code: str, size=2) -> str:
    indent = ' ' * size
    return indent + code.replace('\n', f'\n{indent}')


def byte_size(x: int) -> int:
    return (x.bit_length() + 7) // 8


def to_mask(size: int) -> int:
    return (1 << size) - 1
