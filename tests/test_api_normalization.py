"""Tests for Sunsynk API payload normalization."""

import unittest

from custom_components.sunsynk.api import normalize_key, normalize_monitoring_payloads


class ApiNormalizationTest(unittest.TestCase):
    """Tests for normalizing Sunsynk API payloads."""

    def test_normalize_monitoring_payloads_handles_partial_payloads(self):
        """Partial payloads should produce stable values without raising."""
        values = normalize_monitoring_payloads(
            input_data={
                "pac": 9,
                "pvIV": [
                    {
                        "pvNo": 1,
                        "vpv": "91.5",
                        "ipv": "0.1",
                        "ppv": "9.0",
                        "todayPv": "0.0",
                        "time": "2023-01-07 16:50:17",
                    }
                ],
                "etoday": 1.8,
                "etotal": 375.2,
            },
            grid_data={
                "vip": [{"volt": "233.6", "current": "0.8", "power": 610}],
                "pac": 610,
                "fac": 50.08,
                "etodayFrom": "12.2",
                "etodayTo": "0.0",
                "etotalFrom": "998.5",
                "etotalTo": "48.2",
            },
            battery_data={
                "power": -18,
                "current": "-0.4",
                "voltage": "53.3",
                "temp": "18.7",
                "soc": "20.0",
                "etodayChg": "1.1",
                "etodayDischg": "0.6",
                "etotalChg": "188.5",
                "etotalDischg": "147.9",
            },
        )

        self.assertEqual(values["solar_power"].value, 9.0)
        self.assertEqual(values["solar_power"].unit, "W")
        self.assertEqual(values["pv_1_voltage"].value, 91.5)
        self.assertEqual(
            values["pv_1_voltage"].updated_at, "2023-01-07 16:50:17"
        )
        self.assertEqual(values["grid_import_total"].value, 998.5)
        self.assertEqual(values["grid_phase_1_power"].value, 610)
        self.assertEqual(values["battery_soc"].value, 20.0)
        self.assertEqual(values["battery_power"].value, -18)

    def test_normalize_key_converts_camel_and_dash_case(self):
        """API keys should normalize to snake case."""
        self.assertEqual(
            normalize_key("batteryMaxCurrentCharge"),
            "battery_max_current_charge",
        )
        self.assertEqual(normalize_key("zero-export-power"), "zero_export_power")


if __name__ == "__main__":
    unittest.main()
