import os
import sys
import unittest
from decimal import Decimal

os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from db.reference_thresholds import _extract_measurements, format_threshold_context


class TestReferenceThresholds(unittest.TestCase):

    def test_extracts_latest_numeric_parameter_values(self):
        text = (
            "Pressure was reduced from 0.32 MPa to 0.26 MPa. "
            "The nozzle diameter changed from 200 microns to 150 microns. "
            "Dispensing time is 80 ms."
        )

        result = _extract_measurements(text)

        self.assertEqual(result["pressure"], Decimal("0.26"))
        self.assertEqual(result["nozzle_size"], Decimal("150"))
        self.assertEqual(result["time"], Decimal("80"))

    def test_extracts_diameter_from_mm_value_in_answer(self):
        text = (
            "What is the exact measured diameter if you have it?\n"
            "I feel like it is too large, around 0.95 mm."
        )

        result = _extract_measurements(text)

        self.assertEqual(result["diameter"], Decimal("0.95"))

    def test_formats_threshold_context(self):
        context = format_threshold_context(
            {
                "threshold_row": {
                    "material": "silver epoxy adhesive",
                    "defect_type": "Undersized Dot",
                },
                "checks": [
                    {
                        "parameter": "pressure",
                        "measured": 0.26,
                        "min": 0.3,
                        "target": 0.32,
                        "max": 0.35,
                        "status": "below_min",
                        "interpretation": "Measured value is below the acceptable minimum.",
                    }
                ],
            }
        )

        self.assertIn("Reference Threshold Checks", context)
        self.assertIn("silver epoxy adhesive", context)
        self.assertIn("pressure", context)
        self.assertIn("below_min", context)


if __name__ == "__main__":
    unittest.main()
