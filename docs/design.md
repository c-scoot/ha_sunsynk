# Sunsynk Cloud Native Integration Design

Last reviewed: 2026-05-01.

## Goal

Build a native Home Assistant custom integration for Sunsynk Cloud that starts with dependable read-only monitoring and leaves a safe path toward writes once real-account readback and permissions are proven.

## Current API Understanding

Sunsynk support now points API access to `https://openapi.sunsynk.net`, but the practical Connect API host used by current community clients is `https://api.sunsynk.net`. The current login flow requires a public-key request and RSA PKCS#1 v1.5 password encryption before posting to `/oauth/token/new`.

The first implementation uses these read endpoints:

- `GET /api/v1/inverters`
- `GET /api/v1/inverter/{serial}`
- `GET /api/v1/inverter/{serial}/realtime/input`
- `GET /api/v1/inverter/{serial}/realtime/output`
- `GET /api/v1/inverter/grid/{serial}/realtime`
- `GET /api/v1/inverter/battery/{serial}/realtime`
- `GET /api/v1/inverter/load/{serial}/realtime`
- `GET /api/v1/common/setting/{serial}/read`

Normal polling uses the realtime endpoints. Inverter detail and settings readback are refreshed at most every six hours.

## Polling And API Budget

The default scan interval is 60 seconds and the options flow does not allow values below 60 seconds. This matches the best published Sunsynk Connect data interval found during research. Polling faster would not create fresher samples and would increase cloud load.

Per inverter, each normal refresh can call five realtime endpoints. Detail and settings calls are deliberately slow. The integration records per-inverter API calls in a disabled diagnostic sensor.

## Entity Model

The first sensor set is curated around values needed for monitoring and Energy dashboard decisions:

- Solar power, daily generation, and lifetime generation.
- Grid power, import/export daily counters, and import/export total counters.
- Load power and daily/lifetime load counters.
- Battery SOC, signed battery power, voltage, current, temperature, and charge/discharge counters.
- Inverter output power/frequency and selected diagnostics.

Payload normalization happens in `api.py`. Entity classes consume normalized sample keys and do not know Sunsynk payload quirks.

## Write Discovery

The settings readback endpoint exposes candidate write keys. The most relevant groups discovered so far are:

- System mode and export behavior: `sysWorkMode`, `energyMode`, `solarSell`, `pvMaxLimit`, `zeroExportPower`, `solarMaxSellPower`.
- Six time-of-use slots: `time1on` through `time6on`, `sellTime1` through `sellTime6`, `cap1` through `cap6`, and the matching grid/gen charge flags.
- Battery behavior: `batteryLowCap`, `batteryShutdownCap`, `batteryRestartCap`, `batteryMaxCurrentCharge`, `batteryMaxCurrentDischarge`.

No write service or writable entity is exposed in this pass. Before exposing writes, the project needs:

- Readback confirmation after a write.
- Owner or manager account permission confirmation.
- Validation for unsupported inverter models.
- A rollback or recovery plan for multi-field mode changes.
- A manual recovery note in README.

## Showstopper Check

No architectural showstopper was found for a native integration. The integration is cloud polling rather than local control, so it depends on Sunsynk Connect availability and account permissions. Local Modbus remains a separate possible future track, not part of this first native cloud implementation.
