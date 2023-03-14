from eopsin.prelude import *


# inspired by https://github.com/MuesliSwapTeam/muesliswap-cardano-pool-contracts/blob/main/dex/src/MuesliSwapPools/BatchOrder/Types.hs
@dataclass()
class BatchOrder(PlutusData):
    sender: Address
    receiver: Address
    receiver_datum_hash: Union[Nothing, SomeDatumHash]
    batcher_fee: int
    output_ada: int
    pool_nft_tokenname: TokenName
    script_version: bytes


def validator(d: Anything, r: Anything) -> bytes:
    # this casts the input to BatchOrder - in the type system! In the contract this is a no-op
    # this means that the contract never actually checks if the type fully matches!
    # there may be errors only arising from this implicit cast further downstream
    e: BatchOrder = d
    # this casts the input to bytes - in the type system! In the contract this is a no-op
    r2: bytes = r
    c = e.sender.payment_credential
    # this actually checks that c is of the type PubKeyCredential
    if isinstance(c, PubKeyCredential):
        res = c.credential_hash
    return res + r2
