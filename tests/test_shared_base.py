"""Small tests for the shared dataclasses (stdlib only: python -m unittest)."""

import unittest

from shared.base import Engine, EngineResult, Reason


class TestReason(unittest.TestCase):
    def test_accepts_valid_severity(self):
        for severity in ("info", "low", "medium", "high"):
            self.assertEqual(Reason(severity=severity, text="hello").severity, severity)

    def test_rejects_bad_severity(self):
        with self.assertRaises(ValueError):
            Reason(severity="critical", text="hello")

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            Reason(severity="info", text="   ")


class TestEngineResult(unittest.TestCase):
    def test_defaults(self):
        result = EngineResult(name="demo")
        self.assertEqual(result.risk, 0.0)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.reasons, [])
        self.assertEqual(result.data, {})
        self.assertIsNone(result.error)

    def test_clamps_risk_and_confidence(self):
        self.assertEqual(EngineResult(name="demo", risk=2.5, confidence=-1).risk, 1.0)
        self.assertEqual(EngineResult(name="demo", risk=2.5, confidence=-1).confidence, 0.0)

    def test_error_result_is_valid(self):
        result = EngineResult(name="demo", error="timeout after 5s")
        self.assertEqual(result.error, "timeout after 5s")
        self.assertEqual(result.risk, 0.0)

    def test_requires_name(self):
        with self.assertRaises(ValueError):
            EngineResult(name="")

    def test_rejects_non_dict_data(self):
        with self.assertRaises(ValueError):
            EngineResult(name="demo", data=[])  # type: ignore[arg-type]


class TestEngineContract(unittest.TestCase):
    def test_abstract(self):
        with self.assertRaises(TypeError):
            Engine()  # type: ignore[abstract]

    def test_subclass_signature(self):
        class Demo(Engine):
            name = "demo"

            async def run(self, url: str) -> EngineResult:
                return EngineResult(name=self.name, risk=0.1, confidence=0.5)

        engine = Demo()
        self.assertEqual(engine.name, "demo")
        self.assertTrue(callable(engine.run))


if __name__ == "__main__":
    unittest.main()
