import numpy as np
from .base import ContractFunction
from .utils import indent

SELECTOR_LOAD = 'pc calldataload 0xe0 shr'


def _add_selector_load(base_switch):
    return f'''{SELECTOR_LOAD}
{base_switch}'''


def _generate_lin_switch(fns):
    return '\n'.join(
        f'dup1 0x{sel:08x} eq {name} jumpi'
        for sel, _, name in fns
    ) + '\n0x0 dup1 revert'


def generate_lin_switch(fns):
    return _add_selector_load(_generate_lin_switch(fns))


def _generate_bin_switch(fns, indent_lvl):
    if len(fns) <= 4:
        return _generate_lin_switch(fns)
    mid_point = len(fns) // 2
    lower_leg = fns[:mid_point]
    upper_leg = fns[mid_point:]
    branch_val = lower_leg[-1].selector
    branch_right_label = f'split_0x{branch_val:08x}'
    return f'''dup1 0x{branch_val:08x} lt {branch_right_label} jumpi
{indent(_generate_bin_switch(lower_leg, indent_lvl), indent_lvl)}
{branch_right_label}:
{indent(_generate_bin_switch(upper_leg, indent_lvl), indent_lvl)}'''


def generate_bin_switch(fns, indent_level=2):
    ordered_fns = sorted(fns, key=lambda fn: fn.selector)
    return _add_selector_load(_generate_bin_switch(ordered_fns, indent_level))


def mask_unique(sels, mask):
    return len(sels) == len(set(sels & mask))


def _generate_direct_jump_dests(fns, offset, bits):
    mask = (1 << bits) - 1
    ind_to_fn = {
        (fn.selector >> offset) & mask: fn
        for fn in fns
    }
    hex_digs = (bits + 3) // 4
    return '\n'.join([
        f'dj_dest_0x{hex(i)[2:].zfill(hex_digs)}: ' + (
            'NO_MATCH' if (fn := ind_to_fn.get(i)) is None
            else f'RECEIVE_CHECK({fn.name})' if fn.is_receive
            else f'FUNC_CHECK(0x{fn.selector:08x}, {fn.name})'
        )
        for i in range(1 << bits)
    ])


# Size of power-of-2 padded selector check
BASE_BLOCK_BIT_SIZE = 4


def _generate_simple_mask_direct_jump(fns, direct_mask):
    pass


def generate_direct_jump(fns, max_bit_size=None, receive=False, fallback=False):
    fns = fns.copy()
    if receive:
        fns.append(ContractFunction(0, receive, True))
    total_fns = len(fns)
    bit_size = (total_fns-1).bit_length()
    if max_bit_size is None:
        max_bit_size = bit_size
    if bit_size > max_bit_size:
        raise ValueError(
            f'Functions cannot fit in maximum bit size {max_bit_size}'
        )
    sels = np.array([fn.selector for fn in fns])

    for cur_bit_size in range(bit_size, max_bit_size + 1):
        base_mask = (1 << cur_bit_size) - 1
        if mask_unique(sels, (direct_mask := base_mask << BASE_BLOCK_BIT_SIZE)):
            pass
