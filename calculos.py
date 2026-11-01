"""Exact decimal arithmetic and a single half-up rule for grades over twenty."""
from decimal import Decimal,ROUND_HALF_UP


def decimal(value):return value if isinstance(value,Decimal) else Decimal(str(value))


def rounded(value):return float(decimal(value).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def weighted_average(pairs):
    values=[(decimal(n),decimal(w)) for n,w in pairs if n is not None and decimal(w)>0]
    maximum=sum((w for n,w in values),Decimal(0))
    if not maximum:return None
    return rounded(sum((n*w for n,w in values),Decimal(0))/maximum)


def normalized_total(earned,maximum):
    return rounded(Decimal(20)*decimal(earned)/decimal(maximum))
