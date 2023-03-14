"""
You can define more complex datums using PyCardanos notation.
Every datum/object is a class that inherits from PlutusData and implements dataclass.
If you don't understand what this means, don't worry. Just stick to the way that datums are defined
in these examples.

If something can be either object A or object B, you can create Union[A, B] as a new type.
You can distinguish between A and B using isinstance(x, A) and isinstance(x, B).
IMPORTANT: Make sure that all objects in a Union have different CONSTR_ID values.
The exact value does not matter too much actually, but they need to be different.

Try it out!

```bash
(venv) $ eopsin eval examples/b_datums/a_complex_datum.py '{ "constructor": 0, "fields": [ { "bytes": "0000000000000000000000000000000000" }, { "constructor": 1, "fields": [ { "int": 1000000 }, { "int": 20 } ] } ] }'
> Starting execution
> ------------------
> ------------------
> 20
```
"""
# We import the prelude now, it will bring all values for classes and types
from eopsin.prelude import *


@dataclass()
class Deposit(PlutusData):
    CONSTR_ID = 0
    minimum_lp: int


@dataclass()
class Withdraw(PlutusData):
    CONSTR_ID = 1
    minimum_coin_a: int
    minimum_coin_b: int


OrderStep = Union[Deposit, Withdraw]

# inspired by https://github.com/MuesliSwapTeam/muesliswap-cardano-pool-contracts/blob/main/dex/src/MuesliSwapPools/BatchOrder/Types.hs
@dataclass()
class BatchOrder(PlutusData):
    owner: PubKeyHash
    action: Union[Deposit, Withdraw]


# If some parameter might be ommited, just Union with Nothing and check for the instance at runtime!
def validator(datum: BatchOrder) -> int:
    action = datum.action
    if isinstance(action, Deposit):
        res = action.minimum_lp
    elif isinstance(action, Withdraw):
        res = action.minimum_coin_b
    # note we never initialized res. This means this will
    # throw a NameError if the instances don't match -
    # this is fine, it means that the contract was not invoked correctly!
    return res
