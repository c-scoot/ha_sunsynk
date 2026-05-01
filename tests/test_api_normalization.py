"""Tests for Sunsynk API payload normalization."""

import unittest

from custom_components.sunsynk.api import (
    SYSTEM_MODE_SETTING_FIELDS,
    SunsynkUnsupportedSettingError,
    build_settings_command_payload,
    normalize_key,
    normalize_monitoring_payloads,
    setting_value_matches,
    settings_command_supported,
)


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

    def test_build_settings_command_payload_preserves_expected_body(self):
        """Writable mode updates should preserve the full system-mode payload."""
        settings = _sample_system_mode_settings()

        payload = build_settings_command_payload(
            settings,
            "1234567890",
            {"sysWorkMode": 2},
        )

        self.assertEqual(set(payload), set(SYSTEM_MODE_SETTING_FIELDS))
        self.assertEqual(payload["sn"], "1234567890")
        self.assertEqual(payload["sysWorkMode"], 2)
        self.assertEqual(payload["energyMode"], 0)
        self.assertEqual(payload["peakAndVallery"], 1)
        self.assertEqual(payload["sellTime1"], "00:00")
        self.assertIs(payload["time1on"], True)
        self.assertIs(payload["genTime1on"], False)

    def test_build_settings_command_payload_rejects_partial_readback(self):
        """Missing preserved fields should stop writes before posting to Sunsynk."""
        settings = _sample_system_mode_settings()
        settings.pop("sellTime1")

        self.assertFalse(settings_command_supported(settings, "1234567890"))
        with self.assertRaises(SunsynkUnsupportedSettingError):
            build_settings_command_payload(
                settings,
                "1234567890",
                {"energyMode": 1},
            )

    def test_build_settings_command_payload_rejects_wrong_serial(self):
        """A payload read for one inverter must not be written to another."""
        settings = _sample_system_mode_settings()

        with self.assertRaises(SunsynkUnsupportedSettingError):
            build_settings_command_payload(
                settings,
                "0987654321",
                {"peakAndVallery": 0},
            )

    def test_build_settings_command_payload_validates_supported_values(self):
        """Only known enum values should be accepted for the first write controls."""
        settings = _sample_system_mode_settings()

        with self.assertRaises(SunsynkUnsupportedSettingError):
            build_settings_command_payload(
                settings,
                "1234567890",
                {"sysWorkMode": 9},
            )

    def test_setting_value_matches_normalizes_api_readback(self):
        """Readback confirmation should tolerate numeric strings and booleans."""
        settings = _sample_system_mode_settings()
        settings["energyMode"] = "1"
        settings["peakAndVallery"] = True

        self.assertTrue(setting_value_matches(settings, "energyMode", 1))
        self.assertTrue(setting_value_matches(settings, "peakAndVallery", 1))


def _sample_system_mode_settings():
    """Return a representative system-mode settings readback payload."""
    settings = {field: "" for field in SYSTEM_MODE_SETTING_FIELDS}
    settings.update(
        {
            "sn": "1234567890",
            "safetyType": "0",
            "battMode": "0",
            "solarSell": "0",
            "pvMaxLimit": "100",
            "energyMode": 0,
            "peakAndVallery": 1,
            "sysWorkMode": 1,
            "zeroExportPower": "20",
            "solarMaxSellPower": "5000",
        }
    )

    for index in range(1, 7):
        settings[f"sellTime{index}"] = f"0{index - 1}:00"
        settings[f"sellTime{index}Pac"] = 0
        settings[f"cap{index}"] = 50
        settings[f"sellTime{index}Volt"] = ""
        settings[f"time{index}on"] = index == 1
        settings[f"genTime{index}on"] = False

    for day in (
        "mondayOn",
        "tuesdayOn",
        "wednesdayOn",
        "thursdayOn",
        "fridayOn",
        "saturdayOn",
        "sundayOn",
    ):
        settings[day] = "1"

    return settings


if __name__ == "__main__":
    unittest.main()
