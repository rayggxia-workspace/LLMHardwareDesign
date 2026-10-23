"""Independent exact standard-library oracles, not target implementation."""
from fractions import Fraction
import math


def requant(acc,m,r,bits):
    rounded=round(Fraction(acc*m,2**r))
    return min(2**(bits-1)-1,max(-2**(bits-1),rounded))


def right_shift(value,bits):
    return round(Fraction(value,2**bits))


def multiply(a,b):
    return a*b


def divide(a,b):
    return divmod(a,b)


def square_root(a):
    return math.isqrt(a)
