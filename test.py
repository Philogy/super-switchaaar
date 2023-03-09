from super_switchar.base import ContractFunction
# , _generate_direct_jump_dests, _get_checks_definitions
from super_switchar.generators import generate_direct_jump
from random import randint

if __name__ == '__main__':
    fns = [
        ContractFunction(randint(0, 0xffffffff), f'fn{i:02}', False)
        for i in range(61)
    ]
    print(generate_direct_jump(fns, 2, max_bit_size=8))
