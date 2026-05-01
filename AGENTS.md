# AGENTS.md

## Purpose

This repository is a Home Assistant custom integration for Sunsynk Cloud.
Optimize for reliability, safe API usage, stable entities, and clear user-facing behavior over feature volume.

## Default Balance

Use this default effort split unless the task clearly needs a different ratio:

- Design: 25%. Understand the affected behavior, API contract, entity impact, refresh behavior, and Sunsynk call-budget implications before editing.
- Build: 40%. Implement the smallest coherent change in the correct layer, including any required docs, strings, or service descriptions as part of the same change.
- Validate: 20%. Review the implementation against the design, layer boundaries, entity semantics, API safety, and user-facing coverage before running tests.
- Test: 15%. Run the strongest available automated and manual checks for the exact path that changed.

Do not skip documentation during Build or coverage checks during Validate just because the repo is small.

## Workflow For Every Task

1. Design first. Identify the user-visible outcome, the exact layer that should change, entity stability constraints, and whether the Sunsynk API call budget, polling cadence, or write-followed-by-refresh behavior is affected.
2. Build second. Make the smallest coherent implementation in the correct module and update any required docs, strings, or service descriptions in the same pass.
3. Validate third. Check that the implementation matches the design, stays in the correct layer, preserves entity meaning, handles partial Sunsynk payloads safely, and includes the right documentation updates.
4. Test last. Run the best available automated checks, then summarize manual verification, remaining gaps, and any unverified assumptions.

For non-trivial changes, leave a short design note before broad edits. Keep it compact enough to hand to another specialist agent without passing full repo history.

## Review-Only Tasks

When the user asks for a review, assessment, roadmap, or recommendations, treat it as read-only unless they explicitly ask for implementation.

- Lead with concrete findings, confidence, and risk level.
- Do not suggest enhancements just because an API or file exists. Prefer `no change` when the current behavior is stable and the upside is weak.
- Separate confirmed defects, plausible risks, and speculative opportunities.
- If documentation or external APIs are reviewed, cite the specific source and date-sensitive assumption. Do not pursue API avenues the user has explicitly deferred.
- If the review finds work that should be done, propose the smallest safe change and the tests needed to justify it.

## Repository Map

- `README.md`: installation, setup, behavior, entity semantics, polling, and dashboard guidance.

## Sub-Agent Use

Default to one lead agent. Add specialists only when the task crosses a real boundary or the risk profile benefits from independent ownership. The lead owns the final outcome, sequencing, and go or no-go decisions.

Delegate when a change crosses layers or risks semantic regressions.
Do not delegate tiny single-file fixes, mechanical doc sync, or small presentation-only changes that do not affect semantics, refresh behavior, or API usage.

## Minimal Handoffs

Pass only information that changes the next agent's decision.
Do not pass full transcripts, broad repo summaries, or repeated background.

Use compact handoffs in this format:

Design to Build
- `goal`: one-sentence user-visible outcome
- `scope`: exact files or layers allowed to change
- `non_goals`: what must not change
- `behavior_contract`: expected Home Assistant behavior before and after
- `api_impact`: polling, write path, or Sunsynk call-budget impact
- `entity_contract`: entity IDs, naming, and statistics semantics that must remain stable
- `edge_cases`: partial payloads, stale samples, failed writes, ambiguous inverter ownership
- `docs_needed`: exact docs or translation files to update, or `none`

Build to Validate
- `implemented`: changed files with one-line purpose each
- `design_deltas`: any deviation from design and why
- `risk_points`: most likely regression points
- `api_impact_actual`: actual refresh and call behavior after implementation
- `entity_changes`: added, removed, renamed, or reinterpreted entities or attributes
- `doc_changes`: what was updated or why no update was needed

Validate to Test
- `validation_status`: pass, fail, or partial
- `validated_claims`: what inspection confirmed
- `unverified_claims`: what still needs runtime proof
- `failure_modes`: top remaining risks
- `test_targets`: exact scenarios to run
- `required_commands`: smallest useful commands
- `expected_results`: what success looks like

## Design Rules

- Preserve stable entity meaning and avoid unnecessary entity churn.
- Prefer curated sensors over exposing raw duplicate Sunsynk keys when both represent the same concept.
- Treat rate-limit and daily call-budget impact as part of the design, not an afterthought.
- Keep long-term statistics semantics correct. Daily counters, total counters, and instantaneous power values must not be blurred together.
- Make write paths safe and predictable. Successful writes should refresh or invalidate related cached state promptly.
- If a change requires a preparatory state mutation, make it rollback-safe or order operations so failed writes do not leave the inverter in a new mode.
- If  payload ownership is ambiguous, fail safe. Prefer returning unavailable or raising a handled error over guessing which inverter a payload belongs to.
- Preserve graceful behavior when Sunsynk omits fields, changes naming, or returns partial data.
- Do not broaden scope with opportunistic refactors unless they directly reduce risk in the current task.
- Treat Sunsynk as the source of truth for writable state where the API can safely and cheaply provide readback. If source-of-truth reads are unavailable, expensive, or unreliable, document the fallback hierarchy and expose uncertainty rather than pretending the state is authoritative.

## Build Rules

- Put API quirks and payload normalization in `api.py`, not in entity classes unless the data is purely presentation-specific.
- Put refresh cadence, merge logic, and post-write refresh behavior in `coordinator.py`.
- Keep entity files focused on Home Assistant entity behavior, naming, attributes, and derived values.
- Prefer small helpers over deeply inlined logic when handling Sunsynk naming variants or scheduler/work-mode fallbacks.
- For derived energy or statistics logic, use source timestamps when available and do not treat repeated stale samples as fresh production.
- Preserve backward compatibility for entity IDs, service names, and dashboard-facing behavior whenever practical.
- Add brief comments only for non-obvious Sunsynk quirks, derived calculations, or fallback reasoning.
- Do not add new writable Sunsynk endpoints unless the user explicitly asks for that control or the change is required to fix an existing control. Start with read-only discovery or diagnostics where possible.
- For every writable Sunsynk endpoint, design the readback, refresh, rollback, call-budget impact, unsupported-model behavior, and manual recovery path before implementing the write.
- Prefer documented request methods and payloads in normal polling. If an undocumented fallback is needed, cache success and failure per inverter so unsupported probes do not repeat on every refresh.

## Documentation Rules

- Update `README.md` when changing setup flow, polling behavior, entity naming, entity semantics, Energy dashboard guidance, writable controls, or known API caveats.
- Update `services.yaml` when changing service parameters, meanings, or examples.
- Update `strings.json` and `translations/en.json` when adding or renaming config-flow or UI text.
- If a change is internal-only, document the reasoning with clear commit notes or concise inline comments where the code would otherwise be hard to follow.

## Testing Rules

- Validation must happen before testing. Confirm the change is in the correct layer, preserves entity meaning, and does not introduce unnecessary Sunsynk API usage before running checks.
- Prefer automated tests for normalization logic, rate-limit handling, scheduler/work-mode behavior, derived sensor math, and coordinator refresh decisions.
- If there is no existing test harness for the affected area, it is acceptable to add a small targeted one rather than relying only on manual checks.
- At minimum, run a syntax or import-level validation for touched Python files.
- For changes touching daily reports, timestamps, scheduler state, or derived energy sensors, include rollover, stale-sample, and failed-write recovery scenarios in validation.
- If `python` or `py` is unavailable on PATH, use the bundled workspace Python runtime for syntax or import validation rather than skipping checks.
- For behavior changes, record a manual verification checklist covering the exact user-visible path that changed.
- If testing is partial, say exactly what was verified and what was not.

## Definition Of Done

A task is not done until all of the following are true:

- The change is implemented in the correct layer with scope kept under control.
- User-facing documentation, service descriptions, or UI strings were updated when needed, or a clear note explains why no update was needed.
- Validation was completed before testing and the results were recorded.
- Testing was run at the strongest practical level and the results were recorded.
- Assumptions, tradeoffs, and remaining risks were stated plainly.
- Only the minimum relevant context was handed from one agent to the next.
