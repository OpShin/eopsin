"""
You can also define lists as
attributes for datums

"""
from eopsin.prelude import *


@dataclass()
class D2(PlutusData):
    list_field: List[DatumHash]


def validator(d: D2) -> bool:
    return b"\x01" == d.list_field[0]
