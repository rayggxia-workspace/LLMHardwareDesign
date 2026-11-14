"""Tests for selected TLM service model admission."""

import unittest

from tlm_model_registry import ModelBinding, model_for


KEY = (0, 0x02505001, 0x02504D02, 2, "scope_committed")


class ModelRegistryTest(unittest.TestCase):
    def test_installed_model_is_the_executable_provider(self):
        received = []

        def provider(record):
            received.append(record)
            return lambda done: done()

        binding = ModelBinding(provider, "p-scope-example/1")
        admitted = model_for({KEY: binding}, KEY)
        self.assertIs(admitted, binding)
        self.assertEqual(admitted.identity, "p-scope-example/1")
        admitted.provider(b"descriptor")(lambda: received.append("committed"))
        self.assertEqual(received, [b"descriptor", "committed"])

    def test_all_five_key_fields_must_match(self):
        bindings = {KEY: ModelBinding(lambda record: record, "p-scope-example/1")}
        for index, different in enumerate((1, 0, 0, 1, "service_done")):
            with self.subTest(different_field=index):
                other = (*KEY[:index], different, *KEY[index + 1:])
                self.assertIsNone(model_for(bindings, other))
        self.assertIsNone(model_for({}, KEY))
        self.assertIsNone(model_for({KEY[:-1]: bindings[KEY]}, KEY))

    def test_malformed_keys_fail_closed_before_lookup(self):
        bindings = {KEY: ModelBinding(lambda record: record, "p-scope-example/1")}
        for key in (KEY[:-1], (*KEY, "extra"), (False, *KEY[1:]),
                    (-1, *KEY[1:]), (*KEY[:4], ""), ["incomplete"]):
            with self.subTest(key=key), self.assertRaises(ValueError):
                model_for(bindings, key)

    def test_declarative_model_is_not_an_executable_provider(self):
        with self.assertRaises(TypeError):
            model_for({KEY: {"provider": "alias", "identity": "fake/1"}}, KEY)
        with self.assertRaises(TypeError):
            model_for({KEY: None}, KEY)
        with self.assertRaises(TypeError):
            ModelBinding("alias", "fake/1")
        with self.assertRaises(ValueError):
            ModelBinding(lambda record: record, " ")


if __name__ == "__main__":
    unittest.main()
