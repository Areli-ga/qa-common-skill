---
name: ga-har-sync
description: Analyze new Charles HAR captures for Giggle Academy, compare them with the GA API Flight Deck scenarios, and safely merge genuinely new API requests with dynamic IDs, risk controls, tests, reports, documentation, and secret scanning. Use when the user supplies a new .har/Charles recording, asks to add newly captured app requests, refresh API coverage, compare captures with the existing interface automation project, or maintain the GA user-journey API suite.
---

# GA HAR Increment Sync

Treat each new HAR as evidence, not as a replay script. Inventory it without retaining secrets, identify coverage gaps, then add only stable and useful requests to the maintained scenario layers.

## Workflow

1. Locate the target project. Prefer a path supplied by the user; otherwise search the current workspace for `config/scenarios/core.json` and a `package.json` named `giggle-api-journey`.
2. Read `AGENTS.md`, `README.md`, `docs/architecture.md`, and `docs/har-increment-workflow.md` before editing. Inspect scenario files and existing uncommitted changes.
3. Run `npm run check` before modification when dependencies are available. Record pre-existing failures instead of attributing them to the new HAR.
4. Run the bundled analyzer from this skill directory:

   ```bash
   node scripts/analyze_har.mjs --har /absolute/new.har --project /absolute/project --output /tmp/ga-har-analysis.json
   ```

   Add `--domains host1,host2` only when the capture uses additional owned API hosts. Never copy the HAR into the project or delivery archive.
5. Review the analyzer summary and inspect only candidates needed to understand dependencies. Ignore static assets, polling duplicates, analytics noise, preflight requests, known failures, and requests already represented by a scenario fingerprint.
6. Classify every candidate before editing. Follow [references/ga-project-contract.md](references/ga-project-contract.md).
7. Implement additions in the correct layer:
   - Update `core.json` only when authentication, bootstrap order, or runtime ID extraction changed.
   - Never hand-edit `verified-base.json`; regenerate it only from a verified `interfaces.json` source.
   - Append new HAR-derived steps to `full.json`. Preserve all earlier increments.
8. Replace account-specific values with runtime context. Always dynamicize current user/kid IDs, tokens, device IDs, timestamps, signatures, email, and password. Prefer IDs extracted earlier in the same run. Keep a content ID only when it is a deliberate stable fixture and explain it in the step description.
9. Infer the request header profile from the working project contract, not by copying captured secrets. Recompute MD5 signatures per request and use environment variables for credentials.
10. Add HTTP/business-code assertions and a meaningful slow threshold. Mark non-GET mutations `stateful`; mark generation, AI, voice, upload, download, or paid/external work `costly`. Keep both disabled by default unless the user explicitly changes the scope.
11. Validate in this order:
    - Parse all scenario JSON and confirm step IDs are unique after inheritance.
    - Run `npm run check`.
    - Run the complete production safe scenario when valid test credentials are available and the user has authorized execution.
    - Treat gray HTTP 503 as expected only when no gray release exists; never relabel other failures as expected.
    - Investigate every failure. Replace stale account/content fixtures with runtime extraction when justified; do not weaken assertions to hide a regression.
    - Scan reports and delivery artifacts for real email, password, Authorization, AuthToken, JWT, device ID, and signing key values.
12. Update `docs/har-increment-workflow.md`: source file/date, inventory counts, added/excluded steps, dynamic variables, validation results, known warnings, and the new scenario baseline. Rebuild the delivery archive if one exists.

## Guardrails

- Do not persist raw HAR bodies, response bodies, authentication headers, or credential values.
- Do not mechanically add all observed requests. Preserve semantic coverage with representative calls.
- Do not reuse a guest kid ID after account login.
- Do not overwrite `full.json` when adding an increment; merge its existing `steps` array.
- Do not execute storybook writes, child management, subscription/payment, follow/favorite mutations, or content generation unless the user explicitly includes them.
- Do not start or leave a local server running unless needed for current review. Stop it when the user asks or when validation is complete and no review is pending.

## Handoff

- Lead with the new total coverage and real validation outcome.
- Separate captured, added, already covered, excluded-by-risk, and failed-validation counts.
- Name every failed or slow endpoint and classify it as a product regression, stale fixture, environment limitation, or unresolved issue.
- Link the updated project documentation and delivery artifact. State whether a local service remains running.
- Never print credentials or raw token material.
