"""DynamoDB helpers: floats -> Decimal on write, Decimal -> int/float on read."""
from decimal import Decimal


def to_ddb(o):
    if isinstance(o, float):
        return Decimal(str(o))
    if isinstance(o, dict):
        return {k: to_ddb(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [to_ddb(v) for v in o]
    return o


def from_ddb(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if isinstance(o, dict):
        return {k: from_ddb(v) for k, v in o.items()}
    if isinstance(o, list):
        return [from_ddb(v) for v in o]
    return o
