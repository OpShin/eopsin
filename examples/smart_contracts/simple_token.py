from eopsin.prelude import *


def validator(redeemer: None, context: ScriptContext) -> None:
    purpose = context.purpose
    # whenever tokens should be burned/minted, the minting purpose will be triggered
    if isinstance(purpose, Minting):
        own_pid = purpose.policy_id
    else:
        assert False, "Wrong redeeming purpose"
    # if any of the tokens in the list is going to be minted (positive minting amount)
    if any([x > 0 for x in context.tx_info.mint.get(own_pid, {b"": 0}).values()]):
        # check the script condition
        # in this case simply checking the pubkeyhash of the owner
        # TODO replace this with your own pubkeyhash!
        assert (
            # bytes.fromhex("dc315c289fee4484eda07038393f21dc4e572aff292d7926018725c2")
            b"\xdc1\\(\x9f\xeeD\x84\xed\xa0p89?!\xdcNW*\xff)-y&\x01\x87%\xc2"
            in context.tx_info.signatories
        ), "Required pubkeyhash missing"
    else:
        # we always allow burning!
        pass
