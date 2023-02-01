"""
An implementation of fractions in eopsin

This does not maintain smallest possible notation invariants for the sake of efficiency
- the user has full control over when to normalize the fractions
"""
from dataclasses import dataclass
from pycardano import PlutusData
from eopsin.std.math import *


@dataclass()
class Fraction(PlutusData):
    numerator: int
    denominator: int


def add_fraction(a: Fraction, b: Fraction) -> Fraction:
    return Fraction(
        (a.numerator * b.denominator) + (b.numerator * a.denominator),
        a.denominator * b.numerator,
    )


def neg_fraction(a: Fraction) -> Fraction:
    return Fraction(-a.numerator, a.denominator)


def sub_fraction(a: Fraction, b: Fraction) -> Fraction:
    return add_fraction(a, neg_fraction(b))


def mul_fraction(a: Fraction, b: Fraction) -> Fraction:
    return Fraction(a.numerator * b.numerator, a.denominator * b.denominator)


def norm_signs_fraction(a: Fraction) -> Fraction:
    """Restores the invariant that the denominator is > 0"""
    return Fraction(sign(a.denominator) * a.numerator, abs(a.denominator))


def norm_fraction(a: Fraction) -> Fraction:
    """Restores the invariant that num/denom are in the smallest possible denomination"""
    g = gcd(a.numerator, a.denominator)
    return Fraction(a.numerator // g, a.denominator // g)
