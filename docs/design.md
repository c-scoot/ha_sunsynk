# Sunsynk Cloud Native Integration Design

Last reviewed: 2026-05-01.

## Goal

Build a native Home Assistant custom integration for Sunsynk Cloud that starts with dependable monitoring and adds narrow, readback-confirmed writes only when the payload and permission model are understood.

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

Version 0.1.1 also uses:

- `POST /api/v1/common/setting/{serial}/set`

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

The settings readback endpoint exposes candidate write keys. Version 0.1.1 implements only these first controls:

- `sysWorkMode`: Home Assistant select for system work mode.
- `energyMode`: Home Assistant select for energy pattern.
- `peakAndVallery`: Home Assistant switch for system timer enablement.

Scheduler slot editing is deliberately out of scope for this release. Export controls and battery protection/current controls remain discovery-only candidates.

## 0.1.1 Write Design

The expected system-mode command body is a read-modify-write payload, not a single-key patch. It preserves:

```text
sn, safetyType, battMode, solarSell, pvMaxLimit, energyMode, peakAndVallery,
sysWorkMode, sellTime1..sellTime6, sellTime1Pac..sellTime6Pac, cap1..cap6,
sellTime1Volt..sellTime6Volt, zeroExportPower, solarMaxSellPower,
mondayOn..sundayOn, time1on..time6on, genTime1on..genTime6on
```

For each write:

1. Read current settings from `/read`.
2. Validate the requested value against the supported enum for the field.
3. Build the full command payload from readback and override only the requested key.
4. POST the payload to `/set`.
5. Immediately read settings again.
6. Update Home Assistant state only when readback confirms the requested value.
7. Do not expose controls when required command fields are missing or the settings serial does not match the inverter.

Control-specific contracts:

- `sysWorkMode`: accepts `0` Selling First, `1` Zero-Export + Limited to Load, or `2` Limited to Home.
- `energyMode`: accepts `0` Priority Battery or `1` Priority Load.
- `peakAndVallery`: accepts `0` disabled or `1` enabled.

Unsupported models, partial readback, mismatched serials, failed posts, and unconfirmed writes fail closed. The branch does not attempt rollback because each exposed write changes only one field while preserving the current readback payload; manual recovery is through Sunsynk Connect or a later explicit restore service if real-device testing shows that is needed.

## Showstopper Check

No architectural showstopper was found for a native integration. The integration is cloud polling rather than local control, so it depends on Sunsynk Connect availability and account permissions. Local Modbus remains a separate possible future track, not part of this first native cloud implementation.
