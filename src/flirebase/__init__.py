"""Decode Firebase callable transport values."""

import json
import re

__all__ = ["decode_callable_data"]

_INT64_RANGES = {
    "type.googleapis.com/google.protobuf.Int64Value": (-(2**63), 2**63 - 1),
    "type.googleapis.com/google.protobuf.UInt64Value": (0, 2**64 - 1),
}
_DECIMAL = re.compile(r"-?[0-9]+")
_SIMPLE_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def decode_callable_data(data: object) -> object:
    """Decode callable 64-bit wrappers in a JSON value without mutating it.

    Raise ValueError with the payload path if a recognized wrapper is malformed.
    """
    return _decode(data, "$")


def _decode(data: object, path: str) -> object:
    if isinstance(data, list):
        return [_decode(item, f"{path}[{index}]") for index, item in enumerate(data)]

    if isinstance(data, dict):
        type_url = data.get("@type")
        if isinstance(type_url, str) and type_url in _INT64_RANGES:
            return _decode_integer(data, type_url, path)
        decoded = {}
        for key, value in data.items():
            if isinstance(key, str) and _SIMPLE_KEY.fullmatch(key):
                child_path = f"{path}.{key}"
            else:
                child_path = f"{path}[{json.dumps(str(key))}]"
            decoded[key] = _decode(value, child_path)
        return decoded

    return data


def _decode_integer(wrapper: dict, type_url: str, path: str) -> int:
    type_name = type_url.rsplit(".", 1)[-1]
    context = f"{type_name} wrapper at {path}"
    if wrapper.keys() != {"@type", "value"}:
        raise ValueError(f"{context} must contain exactly @type and value")

    value = wrapper["value"]
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{context} value must be a decimal integer string")

    # Bound the conversion even when the input contains many leading zeros.
    negative = value.startswith("-")
    digits = (value[1:] if negative else value).lstrip("0") or "0"
    lower, upper = _INT64_RANGES[type_url]
    if len(digits) > 20:
        raise ValueError(f"{context} value is outside [{lower}, {upper}]")

    number = int(digits)
    if negative:
        number = -number
    if not lower <= number <= upper:
        raise ValueError(f"{context} value is outside [{lower}, {upper}]")
    return number
