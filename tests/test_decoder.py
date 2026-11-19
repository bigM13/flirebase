from copy import deepcopy
from unittest import TestCase

from flirebase import decode_callable_data

SIGNED = "type.googleapis.com/google.protobuf.Int64Value"
UNSIGNED = "type.googleapis.com/google.protobuf.UInt64Value"


class DecodeCallableDataTests(TestCase):
    def test_nested_wrappers_and_input_preservation(self):
        data = {
            "pages": [{"cursor": {"@type": UNSIGNED, "value": "9007199254740993"}}],
            "offsets": [[{"@type": SIGNED, "value": "-9007199254740993"}]],
        }
        original = deepcopy(data)

        decoded = decode_callable_data(data)

        self.assertEqual(
            decoded,
            {"pages": [{"cursor": 9007199254740993}], "offsets": [[-9007199254740993]]},
        )
        self.assertEqual(data, original)

    def test_integer_limits(self):
        for type_url, number in [
            (SIGNED, -(2**63)),
            (SIGNED, 2**63 - 1),
            (UNSIGNED, 0),
            (UNSIGNED, 2**64 - 1),
        ]:
            with self.subTest(type_url=type_url, number=number):
                result = decode_callable_data({"@type": type_url, "value": str(number)})
                self.assertIs(type(result), int)
                self.assertEqual(result, number)

    def test_out_of_range_values(self):
        for type_url, value in [
            (SIGNED, str(-(2**63) - 1)),
            (SIGNED, str(2**63)),
            (UNSIGNED, "-1"),
            (UNSIGNED, str(2**64)),
            (UNSIGNED, "9" * 5000),
        ]:
            with self.subTest(type_url=type_url, length=len(value)):
                with self.assertRaisesRegex(ValueError, r"at \$ value is outside"):
                    decode_callable_data({"@type": type_url, "value": value})

    def test_malformed_wrapper_shape(self):
        for wrapper in [
            {"@type": SIGNED},
            {"@type": UNSIGNED, "value": "1", "unit": "items"},
        ]:
            with self.subTest(wrapper=wrapper):
                with self.assertRaisesRegex(ValueError, r"at \$\[0\] must contain exactly"):
                    decode_callable_data([wrapper])

    def test_malformed_wrapper_values(self):
        for value in [None, True, 1, 1.0, [], {}, "", " 1", "+1", "1e3", "1.0", "١"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "decimal integer string"):
                    decode_callable_data({"@type": SIGNED, "value": value})

    def test_leading_zeros(self):
        value = "-" + "0" * 5000 + "42"
        self.assertEqual(decode_callable_data({"@type": SIGNED, "value": value}), -42)

    def test_malformed_wrapper_reports_nested_path(self):
        data = {"pages": [{}, {"next.cursor": {"@type": UNSIGNED, "value": True}}]}

        with self.assertRaises(ValueError) as error:
            decode_callable_data(data)

        self.assertIn('$.pages[1]["next.cursor"]', str(error.exception))

    def test_unknown_type_preserves_map_and_decodes_nested_wrapper(self):
        data = {"@type": "example.com/Custom", "value": {"@type": SIGNED, "value": "42"}}

        self.assertEqual(
            decode_callable_data(data),
            {"@type": "example.com/Custom", "value": 42},
        )

    def test_ordinary_values_and_types(self):
        values = [
            None, False, True, 1, 1.0, "1", [], {},
            {"@type": "example.com/Custom", "value": "123"},
            {"@type": ["custom"], "value": "123"},
            {"value": "123"},
        ]
        decoded = decode_callable_data(values)
        self.assertEqual(decoded, values)
        for before, after in zip(values, decoded):
            self.assertIs(type(after), type(before))
