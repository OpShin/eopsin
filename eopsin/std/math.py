""" An implementation of some math operations in eopsin """


def gcd(a: int, b: int):
    while b != 0:
        a, b = b, a % b
    return abs(a)


def sign(a: int):
    return -1 if a < 0 else 1


# TODO these are defined in the default scope in python, consider if shadowing like this is ok or should be taken into impl


def abs(a: int):
    return -a if a < 0 else a


def min(a: int, b: int):
    return a if a <= b else b


def max(a: int, b: int):
    return a if a >= b else b
