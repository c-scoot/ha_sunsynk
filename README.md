# Sunsynk Cloud Home Assistant Integration

Native Home Assistant custom integration for Sunsynk Cloud monitoring.

This is an early read-only foundation. It authenticates against Sunsynk Cloud, discovers inverters on the account, and creates Home Assistant devices and sensors for the main solar, grid, load, inverter, and battery values.

## Current Features

- GUI setup with Sunsynk Connect email and password.
- Automatic inverter discovery from the Sunsynk account.
- Cloud polling with a minimum 60-second interval.
- Curated sensors for:
  - solar power and energy
  - grid power, import, and export
  - load power and energy
  - battery SOC, power, voltage, current, temperature, charge, and discharge
  - inverter output and diagnostics
- Disabled diagnostic sensors for API calls and settings readback.
- Settings readback discovery for future safe write controls.

## Installation

Copy this repository into Home Assistant as a custom integration, or install through HACS once the repository is added as a custom repository.

Expected custom component path:

```text
custom_components/sunsynk
```

Restart Home Assistant, then add **Sunsynk Cloud** from Settings > Devices & services.

## Configuration

The setup flow asks for:

- Sunsynk Connect email address.
- Sunsynk Connect password.
- API base URL, defaulting to `https://api.sunsynk.net`.
- Polling interval in seconds, defaulting to `60`.

The integration will not allow polling below 60 seconds. Sunsynk Connect data is normally refreshed at the logger interval, and polling faster would only increase API traffic.

## Entity Semantics

Power sensors are instantaneous values from realtime endpoints and use watts.

Energy sensors use kilowatt-hours. Daily counters can reset at day rollover and are marked as total-increasing so Home Assistant can handle reset behavior. Lifetime counters represent cumulative totals reported by Sunsynk.

Battery power is the signed value returned by Sunsynk. Confirm the sign convention for your inverter before using it in automations.

## Write Options

This first pass does not expose write services or writable controls.

Research and settings readback show candidate write areas:

- System work mode and export behavior.
- Six time-of-use charge/discharge slots.
- Grid and generator charge flags.
- Target SOC/capacity per slot.
- Battery reserve, shutdown, restart, and current limit values.

Writes need real-account validation before they are safe to expose. Sunsynk documents that settings changes require owner or manager rights on the plant. The integration therefore starts with readback diagnostics and leaves write controls for a later, deliberately tested release.

## API Notes

The current login flow uses a Sunsynk public key, encrypts the password, and posts to `/oauth/token/new`. Monitoring data is read from Sunsynk Connect cloud endpoints. The integration is not local-only and will not update if Sunsynk Cloud, the internet connection, or account permissions are unavailable.

Sources reviewed on 2026-05-01:

- Sunsynk support API access article: <https://sunsynk.freshdesk.com/support/solutions/articles/103000380621-api-access>
- Sunsynk support article on settings permissions: <https://sunsynk.freshdesk.com/support/solutions/articles/103000290688-unable-to-change-inverter-settings>
- openHAB Sunsynk binding documentation for current polling and channel behavior: <https://www.openhab.org/addons/bindings/sunsynk/>
- Current public Sunsynk API client examples: <https://github.com/jamesridgway/sunsynk-api-client>

## Development Status

No showstopper was found for a native Home Assistant integration. The main risk is that Sunsynk Cloud is not a stable, fully documented local API. This project should prefer conservative polling, graceful unavailable states, and carefully validated writes.
