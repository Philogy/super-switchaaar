from collections import namedtuple

ContractFunction = namedtuple(
    'ContractFunction',
    ['selector', 'name', 'is_receive']
)
