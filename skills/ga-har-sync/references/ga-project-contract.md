# GA API Flight Deck contract

Read this reference while classifying or implementing HAR candidates.

## Scenario ownership

| File | Ownership | Allowed changes |
|---|---|---|
| `config/scenarios/core.json` | HAR-derived bootstrap and primary journey | Edit only for auth/order/runtime extraction changes |
| `config/scenarios/verified-base.json` | Generated legacy verified baseline | Regenerate; never hand-edit |
| `config/scenarios/full.json` | Persistent HAR increments | Append deduplicated new steps |

`full` extends `verified-base`; `verified-base` extends `core`. The internal verified baseline must not appear as a normal Web UI choice.

## Header profiles

- `native-ios`: MD5 `timestamp + deviceId + AUTH_KEY`, `DeviceType=ios`, timestamp/device/app version, and selected session token.
- `signed-web`: the same MD5 contract with `DeviceType=web`; omit captured signing/auth values.
- `web`: web device type and session token without MD5.
- `token-bridge`: use only for endpoints proven to require the token in both auth headers.
- `plain`: no session authentication.

Gray keeps the production base URL and adds `k8scluster: true` to every request.

## Dynamic data

Use `{{context.accountKidId}}` after login, never a captured kid ID. Prefer context variables such as `courseId`, `studyPlanId`, `studyUnitId`, `playZoneId`, `pathId`, and `levelId`. Add `extract` rules at the earliest stable producer when a new consumer needs another ID.

Credentials use `{{env.GIGGLE_TEST_EMAIL}}`, `{{base64:env.GIGGLE_TEST_PASSWORD}}`, and server environment configuration. Reports must remain redacted.

## Candidate decisions

- Add safe read requests when they cover a new endpoint, a meaningfully different query mode, or a distinct user-visible function.
- Deduplicate exact method + normalized path + query-key/value-mode combinations.
- Collapse polling and repeated pagination unless pagination itself is under test.
- Keep non-GET requests behind `risk: stateful` and costly/external generation behind `risk: costly`.
- Exclude private share-token URLs from executable scenarios.
- Keep stable content fixture IDs only after a successful real run; dynamicize stale IDs instead of substituting arbitrary captured account data.

## Required verification

Run unit tests/build, then a safe full scenario where authorized. A useful handoff states totals for pass/warning/fail/skip and identifies every anomaly. Secret-scan generated reports and archives before delivery.
