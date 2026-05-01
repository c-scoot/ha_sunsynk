# Validation Record

Last updated: 2026-05-01.

## Scope

Initial native Sunsynk Cloud custom integration scaffold:

- Config flow and options flow.
- Async Sunsynk Cloud client.
- Per-inverter data coordinator.
- Sensor platform.
- README, design note, HACS metadata, and normalization tests.

## Validation

The implementation keeps Sunsynk payload quirks in `api.py`, refresh cadence in `coordinator.py`, and Home Assistant entity behavior in `sensor.py`.

No inverter write endpoint, writable entity, or service is exposed. The only non-read Sunsynk request in the integration code is authentication to `/oauth/token/new`; settings access is readback-only through `/api/v1/common/setting/{serial}/read`.

Polling is constrained to a minimum of 60 seconds in both the config/options flow and runtime setup. Detail and settings readback are gated behind a six-hour slow refresh interval.

Partial realtime payloads are normalized defensively. Missing values become unavailable rather than guessed. Dynamic normalized samples discovered after the first refresh can add sensors without requiring a reload.

## Peer Review Fixes

A peer review agent reported four issues, all addressed:

- Serialized token refresh so concurrent endpoint 401s do not cause repeated independent logins.
- Clamped stored scan intervals at setup time.
- Added a config-flow error for valid accounts that return no inverters.
- Added post-setup dynamic sensor creation for normalized samples that appear after first refresh.

## Tests

Commands run with the bundled workspace Python because `python` was not on PATH:

```text
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile custom_components\sunsynk\__init__.py custom_components\sunsynk\api.py custom_components\sunsynk\coordinator.py custom_components\sunsynk\config_flow.py custom_components\sunsynk\sensor.py custom_components\sunsynk\const.py tests\test_api_normalization.py
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import json, pathlib; [json.loads(pathlib.Path(p).read_text()) for p in ['custom_components/sunsynk/manifest.json','custom_components/sunsynk/strings.json','custom_components/sunsynk/translations/en.json','hacs.json']]; print('json-ok')"
```

Results:

- Python syntax compile: passed.
- Unit tests: passed, 2 tests.
- JSON parsing: passed.

## Remaining Runtime Assumptions

Live Sunsynk account validation has not been run in this workspace. The sign convention for battery power should be confirmed against a real inverter before using it in automations. Settings write controls remain intentionally deferred until readback, permissions, unsupported-model behavior, and recovery paths are tested.
