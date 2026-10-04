"""Small immutable adapter for the BigDecimal operations used by BMF PAP."""
from decimal import Decimal, ROUND_DOWN, ROUND_UP, localcontext


class BigDecimal:
    ROUND_DOWN = ROUND_DOWN
    ROUND_UP = ROUND_UP

    def __init__(self, value=0):
        self.value = value.value if isinstance(value, BigDecimal) else Decimal(str(value))

    @staticmethod
    def valueOf(value):
        return BigDecimal(value)

    def add(self, other):
        return BigDecimal(self.value + BigDecimal(other).value)

    def subtract(self, other):
        return BigDecimal(self.value - BigDecimal(other).value)

    def multiply(self, other):
        return BigDecimal(self.value * BigDecimal(other).value)

    def divide(self, other, scale=None, rounding=ROUND_DOWN):
        with localcontext() as ctx:
            ctx.prec = 50
            result = BigDecimal(self.value / BigDecimal(other).value)
            return result if scale is None else result.setScale(scale, rounding)

    def setScale(self, scale, rounding=ROUND_DOWN):
        return BigDecimal(self.value.quantize(Decimal(1).scaleb(-scale), rounding=rounding))

    def compareTo(self, other):
        other = BigDecimal(other).value
        return int(self.value > other) - int(self.value < other)


BigDecimal.ZERO = BigDecimal(0)
BigDecimal.ONE = BigDecimal(1)
BigDecimal.TEN = BigDecimal(10)
