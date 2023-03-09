import numpy as np
from .base import ContractFunction
from .utils import indent, byte_size, to_mask
from .huff import wrap_as_macro, pad_code

SELECTOR_LOAD = 'pc calldataload 0xe0 shr'


def _generate_lin_switch(fns):
    return '\n'.join(
        f'dup1 0x{fn.selector:08x} eq {fn.name} jumpi'
        for fn in fns
    ) + '\n0x0 dup1 revert'


def generate_lin_switch(fns, indent_lvl):
    return wrap_as_macro(
        'MAIN()',
        [
            SELECTOR_LOAD,
            _generate_lin_switch(fns)
        ],
        indent_lvl=indent_lvl
    )


def _generate_bin_switch(fns, indent_lvl, split_dests_prefix):
    if len(fns) <= 4:
        return _generate_lin_switch(fns)
    mid_point = len(fns) // 2
    lower_leg = fns[:mid_point]
    upper_leg = fns[mid_point:]
    branch_val = lower_leg[-1].selector
    branch_right_label = f'{split_dests_prefix}0x{branch_val:08x}'
    return f'''dup1 0x{branch_val:08x} lt {branch_right_label} jumpi
{indent(_generate_bin_switch(lower_leg, indent_lvl, split_dests_prefix), indent_lvl)}
{branch_right_label}:
{indent(_generate_bin_switch(upper_leg, indent_lvl, split_dests_prefix), indent_lvl)}'''


def generate_bin_switch(fns, indent_lvl, split_dests_prefix='_split_'):
    ordered_fns = sorted(fns, key=lambda fn: fn.selector)
    return wrap_as_macro(
        'MAIN()',
        [
            SELECTOR_LOAD,
            _generate_bin_switch(ordered_fns, indent_lvl, split_dests_prefix)
        ],
        indent_lvl=indent_lvl
    )


NO_MATCH = 'NO_MATCH'
RECEIVE_CHECK = 'RECEIVE_CHECK'
FUNC_CHECK = 'FUNC_CHECK'


def _generate_direct_jump_dests(fns, offset, bits, dests_prefix, skip_zero=False):
    ind_to_fn = {
        (fn.selector >> offset) & to_mask(bits): fn
        for fn in fns
    }
    hex_digs = (bits + 3) // 4
    return '\n'.join([
        f'{dests_prefix}0x{hex(i)[2:].zfill(hex_digs)}: ' + (
            f'{NO_MATCH}()' if (fn := ind_to_fn.get(i)) is None
            else f'{RECEIVE_CHECK}({fn.name})' if fn.is_receive
            else f'{FUNC_CHECK}(0x{fn.selector:08x}, {fn.name})'
        )
        for i in range(skip_zero, 1 << bits)
    ])


# Size of power-of-2 padded selector check
BASE_BLOCK_BIT_SIZE = 4


def _gen_checks_definitions(receive, fallback, indent_lvl):
    if fallback:
        fallback_code = f'{fallback} jump'
        fallback_byte_size = 4
    else:
        fallback_code = 'returndatasize returndatasize revert'
        fallback_byte_size = 3

    check_defs = wrap_as_macro(
        f'{FUNC_CHECK}(selector, final_dest)',
        [
            '<selector> eq <final_dest> jumpi',
            fallback_code,
            pad_code(16 - (11 + fallback_byte_size))
        ],
        takes=1,
        indent_lvl=indent_lvl
    ) + '\n' + wrap_as_macro(
        f'{NO_MATCH}()',
        [
            fallback_code,
            pad_code(16 - (1 + fallback_byte_size))
        ],
        indent_lvl=indent_lvl
    )
    if receive:
        check_defs += '\n' + wrap_as_macro(
            f'{RECEIVE_CHECK}(receive_dest)',
            [
                'calldatasize iszero <receive_dest> jumpi',
                fallback_code,
                pad_code(16 - (7 + fallback_byte_size))

            ]
        )
    return check_defs


ABS_MAX_BIT_SIZE = 10


def gen_empty_labels(fns):
    return [f'{fn.name}:' for fn in fns]


def generate_direct_jump(fns, indent_lvl, max_bit_size=None, receive=False, fallback=False,
                         dests_prefix='dest_'):
    fns = fns.copy()
    if receive:
        fns = [ContractFunction(0, receive, True)] + fns
    total_fns = len(fns)
    bit_size = (total_fns-1).bit_length()
    if max_bit_size is None:
        max_bit_size = ABS_MAX_BIT_SIZE
    max_bit_size = min(ABS_MAX_BIT_SIZE, max_bit_size)
    if bit_size > max_bit_size:
        raise ValueError(
            f'Functions cannot fit in maximum bit size {max_bit_size}'
        )
    sels = np.array([fn.selector for fn in fns])

    base_code = _gen_checks_definitions(receive, fallback, indent_lvl)

    # 5-OP Dest-Deriv Switches
    for cur_bit_size in range(bit_size, max_bit_size + 1):
        # Check for and generate direct shift switch
        if len(set(sels >> (32 - cur_bit_size))) == total_fns:
            final_offset = 28 - cur_bit_size
            return base_code + '\n' + wrap_as_macro(
                'MAIN()',
                [
                    '// load selector',
                    SELECTOR_LOAD,
                    f'dup1 {hex(final_offset)} shr 0xf or',
                    'jump',
                    '// padding',
                    pad_code(2),
                    '',
                    _generate_direct_jump_dests(
                        fns,
                        32 - cur_bit_size,
                        cur_bit_size,
                        dests_prefix
                    ),
                    '\n// Functions',
                    *gen_empty_labels(fns)
                ],
                indent_lvl=indent_lvl
            )
        mask = to_mask(cur_bit_size) << BASE_BLOCK_BIT_SIZE
        # Almost identical to 3-OP and switch except has offset to support 0-indices
        if len(set(sels & mask)) == total_fns:
            return base_code + '\n' + wrap_as_macro(
                'MAIN()',
                [
                    '// load selector',
                    SELECTOR_LOAD,
                    f'dup1 {hex(mask)} and {hex(12 + byte_size(mask))} add',
                    'jump',
                    '',
                    _generate_direct_jump_dests(
                        fns,
                        BASE_BLOCK_BIT_SIZE,
                        cur_bit_size,
                        dests_prefix
                    ),
                    '\n// Functions',
                    *gen_empty_labels(fns)
                ]
            )
