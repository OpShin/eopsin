"""
You can also define dictionaries (maps) as
attributes for datums

"""
from eopsin.prelude import *


@dataclass()
class DictDatum(PlutusData):
    pubkeyhash: bytes


@dataclass()
class DictDatum2(PlutusData):
    dict_field: Dict[int, DictDatum]


def validator(dict_datum_2: DictDatum2) -> bool:
    # field accesses
    # we need to always define a default value!
    a = dict_datum_2.dict_field.get(0, DictDatum(b"0"))
    # accessing keys and values
    # keys and values are lists and can be iterated and indexed
    b = DictDatum(b"\x01") in DictDatum2.dict_field.values()
    c = DictDatum2.dict_field.keys()[1]
    return a and b and c
