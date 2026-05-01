# Validation Record

Last updated: 2026-05-01.

## Scope

0.1.1 Sunsynk Cloud writable system-mode controls:

- `sysWorkMode` select.
- `energyMode` select.
- `peakAndVallery` switch.
- Read-modify-write settings payload construction.
- Immediate post-write settings readback confirmation.
- README, design note, HACS metadata, manifest version, and payload tests.

## Validation

The implementation keeps Sunsynk payload quirks and command-payload construction in `api.py`, refresh/write sequencing in `coordinator.py`, and Home Assistant entity behavior in `select.py` and `switch.py`.

Writes use `POST /api/v1/common/setting/{serial}/set` only after a fresh settings readback. The command payload preserves the expected system-mode field set and changes only the requested key.

The new controls are disabled by default and created only when settings readback contains every required system-mode command field and the readback `sn` matches the inverter serial.

Supported values are constrained to `sysWorkMode` 0/1/2, `energyMode` 0/1, and `peakAndVallery` 0/1. Unsupported models, partial readback, serial mismatch, failed writes, and unconfirmed post-write readback fail closed.

Each successful write costs three settings calls: read current settings, post settings, read settings for confirmation. Normal polling cadence is unchanged and the post-write update does not force a full realtime refresh.

## Previous Peer Review Fixes

A peer review agent reported four issues, all addressed:

- Serialized token refresh so concurrent endpoint 401s do not cause repeated independent logins.
- Clamped stored scan intervals at setup time.
- Added a config-flow error for valid accounts that return no inverters.
- Added post-setup dynamic sensor creation for normalized samples that appear after first refresh.

## Tests

Commands run with the bundled workspace Python:

```text
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile custom_components\sunsynk\__init__.py custom_components\sunsynk\api.py custom_components\sunsynk\coordinator.py custom_components\sunsynk\config_flow.py custom_components\sunsynk\entity.py custom_components\sunsynk\select.py custom_components\sunsynk\sensor.py custom_components\sunsynk\switch.py custom_components\sunsynk\const.py tests\test_api_normalization.py
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests
C:\Users\craig\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import json, pathlib; [json.loads(pathlib.Path(p).read_text()) for p in ['custom_components/sunsynk/manifest.json','custom_components/sunsynk/strings.json','custom_components/sunsynk/translations/en.json','hacs.json']]; print('json-ok')"
git diff --check
```

Results:

- Python syntax compile: passed.
- Unit tests: passed, 7 tests.
- JSON parsing: passed.
- Whitespace diff check: passed.

## Remaining Runtime Assumptions

Live Sunsynk account write validation has not been run in this workspace. The expected payload is based on current community implementation evidence and should be tested against an owner or manager Sunsynk account before enabling controls in production automations.

The integration does not yet expose scheduler slot editing, export controls, battery protection controls, or a restore service. Manual recovery remains through Sunsynk Connect if the cloud accepts a write but later device behavior is unexpected.
