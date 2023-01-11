from eopsin.prelude import *


@dataclass()
class HashDatum(PlutusData):
    valid_hashes: List[DatumHash]


def validator(d: HashDatum) -> bool:
    if b"\x01" in d.valid_hashes:
        print("Valid hash somewhere inside")
    return b"\x01" == d.valid_hashes[0]
