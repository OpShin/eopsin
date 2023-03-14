from eopsin.prelude import *


def validator(n: int) -> int:
    # Tuple assignment works
    a, b = 3, n
    # control flow via if, for and while
    if b < 5:
        print("add")
        a += 5
    while b < 5:
        b += 1
    for i in range(2):
        print("loop")

    # sha256, sha3_256 and blake2b
    from hashlib import sha256 as hsh

    x = hsh(b"123").digest()

    # bytestring slicing, assertions
    assert x[1:3] == b"e" + b"\xa4", "Hash is wrong"

    # create lists, check their length, add up integers
    y = [1, 2]
    return a + len(x) + len(y) if y[0] == 1 else 0
