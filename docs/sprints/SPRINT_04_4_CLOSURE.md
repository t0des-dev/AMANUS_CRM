# SPRINT 04.4 — Final Integrity Closure & Release Readiness

- **Date:** 2026-11-16
- **Branch:** `feature/sprint-04-amnus-agile`
- **Base commit (start of 04.4):** `7edf497dc80dd986624d4c3695b1dffdafdf686e`
- **Final implementation commit:** _pending (created after this report; see final report)_
- **Database (runtime validation only):** `amnus_test_19`
- **Scope:** Close remaining Sprint 04.3 audit blockers for `amnus_agile` without product redesign. No merge, no DB creation/deletion/migration, no `-u all`, no manual DB commits, no Odoo core / `amanus_*` / `business_starter_*` / production changes.

## Preserved artifacts (unchanged)

- `5b7ac38d0a92a9fdc1ed63f85c0e5febc7cca15d` (Sprint 04.1 implementation baseline, preserved in history)
- `7edf497dc80dd986624d4c3695b1dffdafdf686e` (Sprint 04.2 remediation, preserved)
- `docs/sprints/SPRINT_04_1_AUDIT.md` — preserved, untracked
- `docs/sprints/SPRINT_04_2_REMEDIATION.md` — preserved
- `docs/sprints/SPRINT_04_3_AUDIT.md` — preserved, untracked
- `main` at `5b324a04c9e0802a4341bc72163663755adb159d` — unchanged

## Workstream summary

### A. Concurrency and database integrity (F-11, F-12)

**Rows locked / lock order**
- Sprints: `amnus_agile_sprint` rows locked via `SELECT ... FOR UPDATE` in deterministic ascending id order (`_lock_for_workflow`, `_lock_sprints_for_workflow`).
- Stories: `amnus_agile_user_story` rows locked via `SELECT ... FOR UPDATE` in ascending id order before sprint/membership/task-link sensitive mutations.
- Tasks: `project_task` rows locked via `SELECT ... FOR UPDATE` on project-move path when Agile link integrity must be preserved.
- Multi-sprint carry-over: source and target sprint ids locked together in deterministic ascending order before revalidation.
- Burndown sequencing: sprint row is locked before computing `event_sequence`; sequence allocated as `COALESCE(MAX(event_sequence),0)+1` under the sprint lock (PostgreSQL does not allow `FOR UPDATE` on aggregate; reliance is on sprint serialization + DB unique constraint). No manual commits.

**State revalidation after locks**
- Affected sprint/story records invalidated and re-read after lock acquisition in workflow-sensitive paths (assignment, carry-over, create-with-sprint, sprint-state checks, membership open/close decisions, task-link/move checks).

**Database invariants added/retained**
- **Added (PostgreSQL partial unique index):** `amnus_agile_membership_open_story_unique` on `amnus_agile_sprint_membership(story_id) WHERE outcome='active' AND date_removed IS NULL` — enforces at most one open/active membership per story at DB level without conflicting with historical closed/removed rows for the same story or sprint.
- **Retained:** `amnus_agile_membership_sprint_story_unique` (`unique(sprint_id, story_id)`) — preserves append-only historical semantics (no duplicate membership row per sprint/story pair).
- **Retained:** `amnus_agile_burndown_event_unique` (`unique(sprint_id, date, event_sequence)`) — enforces event sequence/date uniqueness per sprint.
- **Retained/relied on:** ORM/server-side guards for sprint terminal-state invariants, workflow transitions, frozen fields, and append-only history; protected fields remain inaccessible to direct public writes.

**Constraint evaluation**
- At most one active/open membership per story: **enforced by PostgreSQL partial unique index** (safe; historical rows unaffected).
- Event sequence uniqueness per sprint/date: **enforced by PostgreSQL unique constraint** (retained) and serialized allocation under sprint row lock.
- Valid sprint terminal-state invariants / frozen metrics / workflow legality: **not safely expressible as simple declarative DB constraints alone** because transitions and frozen baselines depend on controlled server workflows, historical snapshots, and multi-row business validation; protected by deterministic locks, post-lock revalidation, controlled internal write paths, and append-only/history guards.
- `(sprint_id, story_id)` uniqueness retained intentionally to preserve legitimate historical membership semantics (closed historical rows must not be rewritten/reused).

**Transaction behavior**
- No manual transaction commits introduced. ORM/DB constraint violations and validation/user errors abort the operation under normal Odoo transaction semantics (rollback of failed operation/transaction as managed by framework).

**Concurrency tests (genuine parallel)**
- **Not implemented / not verified by true parallel multi-transaction execution** in this environment. Existing Odoo `TransactionCase`/savepoint patterns and the repository restriction to avoid manual DB commits make reliable, non-flaky parallel cursor/transaction races difficult to prove safely on `amnus_test_19`.
- Sequential/DB-invariant tests added in `addons/amnus/amnus_agile/tests/test_closure.py` verify DB rejection of duplicate open membership and duplicate burndown sequence, and runtime protections for F-01–F-09 paths. **These do not constitute proof of parallel race safety.**
- **Status:** concurrency protections implemented and DB invariants strengthened; **parallel guarantees remain unverified** pending reliable multi-transaction test infrastructure/evidence.

### B. Core regression root cause (`amnus_core`, `res_users.notification_type`)

**Observed failure (reproduced):** `psycopg2.errors.NotNullViolation: null value in column "notification_type" of relation "res_users" violates not-null constraint`.

**Evidence gathered**
- Field definition (Odoo 19 core): `C:\Program Files\AmanusERP\odoo\addons\mail\models\res_users.py` defines `notification_type = fields.Selection(..., 'Notification', required=True, default='email', compute='_compute_notification_type', inverse='_inverse_notification_type', store=True, help=...)` (mail-owned stored required field).
- AMNUS fixture issue: `amnus_core` tests created `res.users` without `notification_type` in `addons/amnus/amnus_core/tests/test_security.py` and `addons/amnus/amnus_core/tests/test_amnus_audit_log.py`.
- **Fix applied (AMNUS):** conditional `notification_type='email'` added to affected fixture user creations when `notification_type` exists in `res.users` fields (compatibility/fixture hardening).
- **Runtime result after fix:** `-u amnus_core,mail --test-enable --test-tags amnus_core --stop-after-init` on `amnus_test_19` still failed **0 failed, 11 error(s) of 34 tests, exit 1** (log: `$env:TEMP\core_044.log`, 2026-11-16 09:26:39+). Traceback/SQL shows inserts into `res_users` omitting `notification_type` for patched test cases, indicating fixture behavior not effective in the executed test context or registry/loading/context mismatch not yet conclusively isolated.
- `amnus_core` manifest depends only on `base`, `base_setup` (no `mail` dependency). Installed/loaded runtime in test DB includes `mail` (42 modules loaded during run), consistent with DB-level NOT NULL constraint ownership by mail.
- Prior to Sprint 04.2 was not conclusively proven in available evidence; failure remains reproducible in tested isolated-upgrade/tagged runs on `amnus_test_19`. No evidence that 04.4 Agile code changes introduced it.

**Root-cause conclusion:** **Unresolved / not conclusively established.** Likely interaction between mail-owned required stored field and AMNUS core test fixture/registry/test-runner context in this database, but definitive cause and a verified supported full-registry procedure producing a passing `amnus_core` suite were not established in this session. **Not labeled purely environmental without evidence; not claimed fixed.**

### C. Translation regeneration

**Workflow executed (Odoo 19, `amnus_test_19`)**
- POT export: `C:\Program Files\AmanusERP\python\python.exe C:\Program Files\AmanusERP\odoo\odoo-bin i18n export -c config/amnus-test.conf -d amnus_test_19 -l pot -o addons/amnus/amnus_agile/i18n/amnus_agile.pot amnus_agile` → **exit 0**.
- `fr_FR`/`ar_SA` export attempts: same command with `-l fr_FR` / `-l ar_SA` → **exit 1**, `error: No valid language has been provided` (DB installed languages: `[('en_US', 'English (US)', True)]`; no fr/ar loaded in `amnus_test_19`).
- Merge/update: `polib` merge of new POT into existing `fr_FR.po` and `ar_SA.po`, preserving existing translations and metadata where present, refreshing occurrences/source refs to current POT, removing obsolete entries no longer in POT.

**Counts**
| Artifact | Total entries (msgid != "") | Translated | Untranslated | Obsolete entries |
|---|---:|---:|---:|---:|
| `amnus_agile.pot` | 235 | n/a | n/a | 0 |
| `fr_FR.po` | 235 | 190 | 45 | 0 (2 obsolete removed during merge) |
| `ar_SA.po` | 235 | 190 | 45 | 0 (2 obsolete removed during merge) |

**Validation**
- `polib` parse/load succeeded for POT/FR/AR after merge (`PO_PARSE_OK`).
- `msgfmt` not available in environment; no compiled `.mo` artifacts generated. Visual RTL validation **not performed** (not claimed).

### D. Runtime verification of F-01 through F-09

Runtime verification performed via direct ORM/model calls in automated tests on `amnus_test_19` (`amnus_agile` suite, including `test_closure.py`), asserting resulting state and/or historical records. No existing tests weakened/removed.

| Finding | Runtime/direct ORM verification | Result | Evidence |
|---|---|---|---|
| F-01 | Direct writes to frozen sprint metrics blocked; recomputation/history preserved after closure | Pass | `test_closure.test_f01_frozen_metrics_runtime_direct_orm`, existing remediation/sprint tests |
| F-02 | Linked task move to other project/company or detach rejected; task project/company unchanged | Pass | `test_closure.test_f02_task_move_and_disclosure_runtime`, `test_remediation`/`test_user_story` coverage |
| F-03 | Direct sprint state writes rejected | Pass | `test_closure.test_f03_direct_sprint_state_write_blocked_runtime` |
| F-04 | Invalid sprint/story creation and invalid assignments rejected | Pass | `test_closure.test_f04_invalid_creation_blocked_runtime`, existing tests |
| F-05 | Destructive delete/unlink of historical records rejected where protected | Pass | `test_closure.test_f05_historical_records_not_destructively_deleted_runtime` |
| F-06 | Assignment to closed/cancelled sprint rejected | Pass | `test_closure.test_f06_closed_sprint_assignment_rejected_runtime` |
| F-07 | Carry-over from closed source rejected; source history not rewritten | Pass | `test_closure.test_f07_closed_source_carry_over_preserves_history_runtime` |
| F-08 | Dated burndown events recorded/ordered and immutable; historical scope preserved | Pass | `test_closure.test_f08_dated_events_preserve_history_runtime`, remediation tests |
| F-09 | Direct story state writes/bypass rejected; workflow transition required | Pass | `test_closure.test_f09_direct_story_state_write_and_invalid_workflow_bypass_runtime` |

## Mapping of remaining Sprint 04.3 findings

| 04.3 finding | Implementation change | DB invariant / ORM guard | Regression test | Verification result | Residual limitation |
|---|---|---|---|---|---|
| F-11 (concurrent membership / sprint workflow races) | Deterministic sprint/story/task row locks, ascending lock order, carry-over multi-sprint lock ordering, post-lock invalidation/revalidation, sprint locking in burndown event recording and membership-sensitive paths | Partial unique index `amnus_agile_membership_open_story_unique` (one open story membership globally), retained `unique(sprint_id,story_id)`; ORM guards for open sprint/state/relations | Existing agile suite + `test_closure` DB invariant `test_db_partial_unique_open_membership_per_story` | Code/DB protections in place; agile suite 98/0/0 exit 0 | **True parallel multi-transaction races not demonstrated** in this environment; parallel safety unverified |
| F-12 (concurrent burndown/event sequence, task/story link races) | Sprint-row-serialized burndown sequencing, task/story row locks on move/link-sensitive paths, deterministic lock ordering | Retained `unique(sprint_id,date,event_sequence)`; sprint lock serializes MAX+1 allocation; task/story FK/guards preserved | Existing burndown/remediation tests + `test_closure.test_burndown_event_sequence_uniqueness_db` | Code/DB protections in place; agile suite 98/0/0 exit 0 | **True parallel allocation collision test not demonstrated**; parallel safety unverified |
| Core regression (`amnus_core` NotNullViolation on `res_users.notification_type`) | `amnus_core` test fixtures hardened to set `notification_type='email'` when field exists | N/A (no core schema/workflow change) | `amnus_core` suite re-run attempted (`-u amnus_core,mail --test-enable --test-tags amnus_core`) | **0 failed, 11 errors / 34 tests, exit 1** (same NotNullViolation signature) | **Root cause unresolved/not conclusively established**; no verified passing supported full-registry procedure obtained |
| Translations stale/incomplete for current strings | POT regenerated from DB/export; FR/AR merged against new POT preserving translations and current refs | N/A | `polib` parse validation | POT/FR/AR parse OK; counts reported | 45 untranslated in FR/AR; fr/ar DB export unavailable (only en_US installed); no visual RTL validation |
| Runtime re-verification of F-01–F-09 | No behavior weakening; closure tests added for direct ORM/runtime paths | Existing + strengthened guards/invariants exercised | `addons/amnus/amnus_agile/tests/test_closure.py` (registered in `tests/__init__.py`) and full `amnus_agile` suite | **98 tests, 0 failed, 0 errors, exit 0** | Based on automated ORM/runtime tests in `amnus_test_19`; no UI/RPC-manual/visual claims beyond tested paths |

## Technical documentation

- No additional technical behavior docs required changes beyond this closure record and existing Sprint 04.2/04.3 context; implementation changes are integrity-hardening (locks/DB invariant/serialization) consistent with documented remediation intent.

## Residual risks / limitations

1. **Concurrency safety not proven in parallel:** no reliable multi-transaction/cursor race tests executed; F-11/F-12 remain **unverified by parallel evidence** despite code/DB hardening.
2. **`amnus_core` regression unresolved:** 11/34 errors persist in tested runs; supported full-registry passing procedure not demonstrated.
3. **Translations:** 45 untranslated strings remain in FR/AR; language packs not installed in `amnus_test_19`; no visual RTL validation.
4. **No merge/rebase performed;** final independent audit remains mandatory.

## Final status

**BLOCKED**

Blocking reasons: unresolved/unverified `amnus_core` regression in tested execution, and F-11/F-12 parallel race guarantees not demonstrated by genuine multi-transaction tests (DB/code protections added but unproven under true concurrency).
