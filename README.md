# Flirebase

Flirebase decodes 64-bit integer wrappers in Firebase callable payloads sent
from Flutter to Python Cloud Functions. It requires Python 3.10 or later and
has no runtime dependencies.

Install from a checkout with `python -m pip install .`.

## Before and after

```python
from flirebase import decode_callable_data

payload = {
    "pages": [
        {
            "cursor": {
                "@type": "type.googleapis.com/google.protobuf.UInt64Value",
                "value": "9007199254740993",
            },
            "ready": True,
        }
    ]
}

data = decode_callable_data(payload)
assert data == {"pages": [{"cursor": 9007199254740993, "ready": True}]}
```

The decoder follows the wrapper shapes documented by Firebase. It recognizes
the full `Int64Value` and `UInt64Value` type URLs and requires exactly
`@type` and `value`. Each value must be an ASCII decimal integer string in
the corresponding 64-bit range. Malformed recognized wrappers raise
`ValueError` with the wrapper's location, such as `$.pages[0].cursor`. The root
of the payload is `$`. Ordinary JSON values retain their types, and maps with unknown
type tags retain their fields. The input stays unchanged.
[Firebase callable protocol](https://firebase.google.com/docs/functions/callable-reference#serialization)

## Python Firebase callable

```python
from firebase_functions import https_fn
from flirebase import decode_callable_data


@https_fn.on_call()
def acknowledge_page(request: https_fn.CallableRequest) -> dict[str, str]:
    try:
        data = decode_callable_data(request.data)
    except ValueError as exc:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message=str(exc),
        ) from exc

    if not isinstance(data, dict) or type(data.get("cursor")) is not int:
        raise https_fn.HttpsError(
            code=https_fn.FunctionsErrorCode.INVALID_ARGUMENT,
            message="An integer cursor is required.",
        )

    return {"cursor": str(data["cursor"])}
```

Flirebase handles transport decoding. Apply application-specific validation
after decoding.

## Tests

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```
