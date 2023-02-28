from eopsin.prelude import *


@dataclass()
class PaymentChannel(PlutusData):
    balance_alice: int
    pubkeyhash_alice: bytes
    balance_bob: int
    pubkeyhash_bob: bytes
    nonce: int


@dataclass()
class MicropaymentAlice(PlutusData):
    """Alice pays Bob amount x"""

    CONSTR_ID = 0  # Needed to distinguish different datums
    amount: int
    # The signature of str(amount), signed with alice's secret key
    sig: bytes
    nonce: int


@dataclass()
class MicropaymentBob(PlutusData):
    """Bob pays Alice amount x"""

    CONSTR_ID = 1  # Needed to distinguish different datums
    amount: int
    # The signature of str(amount), signed with bob's secret key
    sig: bytes
    nonce: int


Micropayment = Union[MicropaymentAlice, MicropaymentBob]


@dataclass()
class Micropayments(PlutusData):
    """A sequence of micropayments to be applied to the channel"""

    CONSTR_ID = 0
    payments: List[Micropayment]


@dataclass()
class TearDown(PlutusData):
    """The microchannel is torn down and all participants receive their amounts. Can be initiated by any party"""

    CONSTR_ID = 1


# The setup is implicit! Just send a UTxO to the channel address with the correct datum & amounts
ChannelAction = Union[Micropayments, TearDown]


def validator(
    datum: PaymentChannel, redeemer: ChannelAction, context: ScriptContext
) -> None:
    if isinstance(redeemer, TearDown):
        # Ensure that either party signed this request
        assert (
            datum.pubkeyhash_alice in context.tx_info.signatories
            or datum.pubkeyhash_bob in context.tx_info.signatories
        ), "Neither Alice nor Bob signed the transaction"
        # Ensure that all participants receive their amounts
        amount_alice = 0
        amount_bob = 0
        for o in context.tx_info.outputs:
            # Note: in a real world scenario, you will want to make sure the stake key hash matches too!
            addr_credential = o.address.credential
            if isinstance(addr_credential, PubKeyCredential):
                pkh = addr_credential.pubkeyhash
            elif isinstance(addr_credential, ScriptCredential):
                pkh = addr_credential.validator_hash
            else:
                assert False, "Impossible output address"
            if pkh == datum.pubkeyhash_alice:
                amount_alice += o.value.get(b"", {b"": 0}).get(b"", 0)
            elif pkh == datum.pubkeyhash_bob:
                amount_bob += o.value.get(b"", {b"": 0}).get(b"", 0)
        assert amount_alice >= datum.balance_alice, (
            "Alice does not receive enough, expecting "
            + str(datum.balance_alice)
            + ", receiving "
            + str(amount_alice)
        )
        assert amount_bob >= datum.balance_bob, (
            "Bob does not receive enough, expecting "
            + str(datum.balance_bob)
            + ", receiving "
            + str(amount_bob)
        )
        # That's it!
    elif isinstance(redeemer, Micropayments):
        # Squash apply the micropayments
        balance_alice = datum.balance_alice
        balance_bob = datum.balance_bob
        nonce = datum.nonce
        # Ensure that the payments are all valid and accumulate state
        for payment in redeemer.payments:
            assert payment.nonce > nonce, "Invalid nonce, replay attack detected"
            assert payment.amount > 0, "Invalid amount transfer, must be positive"
            nonce = payment.nonce
            if isinstance(payment, MicropaymentAlice):
                assert verify(
                    datum.pubkeyhash_alice,
                    str(payment.amount).encode("utf8"),
                    payment.sig,
                ), "Invalid signature of Alice for micropayment"
                balance_alice -= payment.amount
                balance_bob += payment.amount
            elif isinstance(payment, MicropaymentBob):
                assert verify(
                    datum.pubkeyhash_bob,
                    str(payment.amount).encode("utf8"),
                    payment.sig,
                ), "Invalid signature of Bob for micropayment"
                balance_alice += payment.amount
                balance_bob -= payment.amount
            else:
                assert False, "Invalid type of micropayment!"

        # we cast the purpose to spending, every other purpose does not make sense
        purpose: Spending = context.purpose
        own_tx_out_ref = context.purpose.tx_out_ref
        # this stunt is just to find the output that goes to the same address as the input we are validating to be spent
        own_tx_out = [i for i in context.tx_info.inputs if i.out_ref == own_tx_out_ref][
            0
        ].resolved
        own_address = own_tx_out.address
        cont_tx_out = [o for o in context.tx_info.outputs if o.address == own_address][
            0
        ]
        # The value = locked tokens must not change
        assert (
            cont_tx_out.value == own_tx_out.value
        ), "Value of payment channel has changed"
        cont_datum = cont_tx_out.datum
        if isinstance(cont_datum, SomeOutputDatum):
            # Ensure that the state is correctly updated
            assert cont_datum.datum == PaymentChannel(
                balance_alice,
                datum.pubkeyhash_alice,
                balance_bob,
                datum.pubkeyhash_bob,
                nonce,
            )
        else:
            assert False, "Must inline attached datum"
    else:
        # Other redeemers are not allowed!
        assert False, "Wrong redeemer passed!"
