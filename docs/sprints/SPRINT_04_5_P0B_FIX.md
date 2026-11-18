# SPRINT 04.5 — P0-B Fix
## `amnus_core` `res_users.notification_type` regression

- **Date:** 2026-11-17
- **Branch:** `feature/sprint-04-amnus-agile`
- **Starting HEAD:** `2c552065193c5c0af3cc537f1411a80b019c342b`
- **Final commit:** `4e6343f` (see Git section)
- **`main` (unchanged):** `5b324a04c9e0802a4341bc72163663755adb159d`
- **Database:** `amnus_test_19` only (`config\amnus-test.conf`, `db_name=amnus_test_19`, `db_filter=^amnus_test_19$`)
- **Scope:** Narrow AMNUS test-fix only (no Odoo core, no DB schema, no manifest dependency change, no production behavior change)

## 1. Diagnostic baseline and original error
- **Previous result (Sprint 04.4 / P0-B diagnostic):** `amnus_core` tagged suite (`--test-tags amnus_core`) — **34 tests, 0 failed, 11 errors, exit 1** in all three contexts (A: `-u amnus_core`, B: `-u amnus_core,mail`, C: no `-u`, full installed registry context).
- **Exception:** `psycopg2.errors.NotNullViolation: null value in column "notification_type" of relation "res_users" violates not-null constraint`.
- **Observed SQL (diagnostic):** `INSERT INTO "res_users"` omitted `notification_type` (e.g. columns `active, company_id, create_date, create_uid, login, partner_id, write_date, write_uid` only).
- **DB schema (verified):** `res_users.notification_type` is `NOT NULL`, no SQL default (`information_schema`: `is_nullable='NO', column_default=None`).
- **Odoo 19 source:** `C:\Program Files\AmanusERP\odoo\addons\mail\models\res_users.py` defines `notification_type` as required stored Selection with `default='email'`, `compute='_compute_notification_type'`, `inverse='_inverse_notification_type'`, `store=True` (mail extension to `res.users`).

## 2. Phase A — Registry state at the exact failing create call (runtime evidence)
**Failing test (reproduced for instrumentation):** `odoo.addons.amnus_core.tests.test_amnus_audit_log.TestAmnusAuditLog.test_audit_user_id_not_forgeable`  
**Command context:** `-u amnus_core --test-enable --test-tags /amnus_core:TestAmnusAuditLog.test_audit_user_id_not_forgeable --stop-after-init` on `amnus_test_19` (log `%TEMP%\amnus_core_p0b_diag_single.log`, exit 1, 1 error).  
**Instrumentation:** temporary diagnostic prints added in-test immediately before `self.env["res.users"].create(vals)`, captured, then reverted (no diagnostic code left; `git diff` clean after revert).

**Observed at failure point (same execution context):**
- `notification_type in self.env['res.users']._fields`: **`False`**
- `vals` passed to `create()`: **`{'name': 'Impersonated User', 'login': 'impersonated_user'}`** (no `notification_type`)
- `model_class`: `<class 'odoo.orm.models.res.users'>`
- **MRO (first entries):** `odoo.orm.models.res.users`, `odoo.addons.web_tour.models.res_users.ResUsers`, `odoo.addons.resource.models.res_users.ResUsers`, `odoo.addons.bus.models.res_users.ResUsers`, `odoo.addons.base_setup.models.res_users.ResUsers`, `odoo.addons.base_import.models.base_import.ResUsers`, `odoo.addons.auth_totp.models.res_users.ResUsers`, `odoo.addons.web.models.res_users.ResUsers`, `odoo.addons.base.models.res_users.UsersMultiCompany`, `odoo.addons.base.models.res_users.ResUsers` — **no `mail.models.res_users.ResUsers`**
- `registry_keys_has_mail` (`'mail.message' in self.env.registry.models`): **`False`**
- `context`: `{}`; `default_get(['login'])`: `{}` (diagnostic requested `notification_type` only if field present)

**Traceback/call path:** test method → `env["res.users"].create(vals)` → `base.models.res_users.create` (base overrides only) → ORM `_create` → SQL INSERT missing `notification_type` → `NotNullViolation`.

## 3. `notification_type` metadata at that point
- **In failing test registry:** field **not present** in `res.users._fields` (no runtime field metadata available in that environment).
- **Expected when mail extension loaded (reference):** required stored Selection, default `'email'`, compute/inverse/store as defined by mail (confirmed in Odoo 19 source and full-registry shell on same DB).

## 4. Actual `vals` immediately before create
- `{'name': 'Impersonated User', 'login': 'impersonated_user'}` (all 11 failures followed equivalent AMNUS fixture paths producing vals without `notification_type` because the conditional `if "notification_type" in ..._fields` evaluated false in that execution context).

## 5. Root cause confirmed by runtime evidence
**Gate result: Case B — Field does not exist in the failing registry.**

`amnus_core` tests were tagged `at_install` (and `-post_install`), so they executed during module load/installation phase before the `mail` model extension was composed into the registry for that run, even though `mail` is installed and the DB schema includes mail-owned `res_users.notification_type NOT NULL` (no SQL default). In that registry state, `res.users` had no `notification_type` field/compute/default behavior, fixture conditionals did not inject a value, and ORM/base insert omitted the column required by the database.

**Supporting evidence:** run B load order showed `Loading module amnus_core (15/42)` before `Loading module mail (17/42)`; identical 11 failures in A/B/C; runtime inspection showed mail absent from registry/MRO and field absent from `_fields` at create time. `amnus_core` manifest depends only on `base, base_setup` (no `mail`), so no dependency guarantees mail is loaded before core tests.

**Classification:** AMNUS test scheduling/fixture-compatibility defect (tests running in a registry state incompatible with installed DB schema) with contributing test-runner/registry-context interaction (at_install execution before mail load). Not an Odoo core/mail schema defect.

## 6. Chosen fix and why alternatives were rejected
**Implemented (narrowest correct fix):** changed `amnus_core` test tags from `@tagged("standard", "amnus_core", "at_install", "-post_install")` to `@tagged("standard", "amnus_core", "post_install", "-at_install")` in all core test modules so tests run after modules are loaded in post-install phase, where the fully composed registry (including `mail`) matches the installed database schema.

**Why chosen:** test-runner/test-loading correction within `addons/amnus/amnus_core/tests/` only; no production code changes; no manifest dependency change; preserves existing assertions/behavior; ensures compatible registry+schema for user creation in mail-installed DB.

**Alternatives rejected:**
- *Blindly pass `notification_type` when field absent in registry:* not safe/supported in that model state (field unknown to ORM model) and does not address registry/schema mismatch; DB still requires column while ORM model lacks field.
- *Add `mail` to `amnus_core` manifest:* unnecessary production dependency change not justified by AMNUS core runtime functionality (would be added mainly to satisfy test/load ordering in this DB context).
- *Direct SQL / schema change / fake model field / core modification:* forbidden or inappropriate.
- *Leaving conditional fixture logic only:* already present and insufficient in Case B context (kept as defense-in-depth, no harm).

## 7. Files changed
- `addons/amnus/amnus_core/tests/test_amnus_audit_log.py` (tag only)
- `addons/amnus/amnus_core/tests/test_security.py` (tag only)
- `addons/amnus/amnus_core/tests/test_config.py` (tag only)
- `addons/amnus/amnus_core/tests/test_amnus_tag.py` (tag only)
- `docs/sprints/SPRINT_04_5_P0B_FIX.md` (this report)

No manifest, production model, translation, config, core, legacy addon, or schema changes.

## 8. A/B/C test commands and results (sequential, `amnus_test_19` verified before each run)

| Run | Command | Exit | Tests | Failed | Errors | Log |
|---|---|---:|---:|---:|---:|---|
| A (core only) | `"C:\Program Files\AmanusERP\python\python.exe" "C:\Program Files\AmanusERP\odoo\odoo-bin" -c config/amnus-test.conf -d amnus_test_19 -u amnus_core --test-enable --test-tags amnus_core --stop-after-init --logfile "%TEMP%\amnus_core_p0b_fix_A.log" --log-handler odoo.tests.result:INFO --log-handler odoo.modules.loading:INFO` | **0** | 34 | 0 | 0 | `%TEMP%\amnus_core_p0b_fix_A.log` |
| B (core + mail) | same with `-u amnus_core,mail` | **0** | 34 | 0 | 0 | `%TEMP%\amnus_core_p0b_fix_B.log` |
| C (existing registry, no -u) | `"C:\Program Files\AmanusERP\python\python.exe" "C:\Program Files\AmanusERP\odoo\odoo-bin" -c config/amnus-test.conf -d amnus_test_19 --test-enable --test-tags amnus_core --stop-after-init --logfile "%TEMP%\amnus_core_p0b_fix_C.log" --log-handler odoo.tests.result:INFO --log-handler odoo.modules.loading:INFO` | **0** | 34 | 0 | 0 | `%TEMP%\amnus_core_p0b_fix_C.log` |

All three contexts: **34 tests, 0 failed, 0 errors, exit 0**.

## 9. Full Core regression result
| Module | Command | Exit | Tests | Failed | Errors | Skipped | Log |
|---|---|---:|---:|---:|---:|---:|---|
| `amnus_core` | `... -u amnus_core --test-enable --test-tags amnus_core --stop-after-init` | **0** | 34 | 0 | 0 | 0 (not reported) | `%TEMP%\amnus_core_reg.log` |

## 10. CRM/Projects/Agile regression results (sequential, after A/B/C)
| Module | Command | Exit | Tests | Failed | Errors | Skipped | Log / note |
|---|---|---:|---:|---:|---:|---:|---|
| `amnus_crm` | `... -u amnus_crm --test-enable --test-tags amnus_crm --stop-after-init` | **0** | 23 | 0 | 0 | 0 | `%TEMP%\amnus_crm_reg.log` |
| `amnus_projects` | `... -u amnus_projects --test-enable --test-tags amnus_projects --stop-after-init` | **0** | 61 | 0 | 0 | 0 | `%TEMP%\amnus_projects_reg2.log` (valid sequential rerun). *Note: an earlier accidental parallel invocation against `amnus_test_19` alongside CRM returned exit -1 / no result and was discarded; corrected by sequential rerun.* |
| `amnus_agile` | `... -u amnus_agile --test-enable --test-tags amnus_agile --stop-after-init` | **0** | 98 | 0 | 0 | 0 | `%TEMP%\amnus_agile_reg.log` |

## 11. Python/XML/manifest validation
- `python -m py_compile` on modified files (`test_amnus_audit_log.py`, `test_security.py`, `test_config.py`, `test_amnus_tag.py`): **exit 0**.
- `amnus_core/__manifest__.py` AST parse: **OK** (unchanged).
- No XML modified.
- `git diff --check`: **clean** (exit 0).
- Final diff limited to 4 test tag lines (+ doc). No assertions weakened/removed, no production logic changes, no direct SQL, no manual commits, no dependency/manifest changes.

## 12. Remaining risks
- **P0-B:** root cause resolved for observed contexts and all required A/B/C + regression suites pass in this environment. Residual risk is low/standard: tests now depend on post-install (full registry) execution, which is appropriate given mail-installed DB schema.
- **Sprint 04.5 broader blockers remain (out of P0-B scope):** P0-A genuine multi-transaction concurrency verification (C-01–C-06) and P1 translation validation/loading/RTL gaps as defined in Sprint 04.5 objectives.

## 13. Git branch and commit
- **Branch:** `feature/sprint-04-amnus-agile`
- **Commit:** `4e6343fd6454d5e86d7d03065959cc56f99bd8e4` — `fix(amnus_core): resolve notification type test regression`
- **Staged/committed intentionally:** 4 modified core test files + `docs/sprints/SPRINT_04_5_P0B_FIX.md`
- **Preserved untracked (not staged):** `docs/sprints/SPRINT_04_1_AUDIT.md`, `docs/sprints/SPRINT_04_3_AUDIT.md`

## 14. Explicit confirmation of no merge
- **No merge into `main`. No rebase/reset/force-push/push/stash/clean. `main` remains `5b324a04c9e0802a4341bc72163663755adb159d`.** Final `git status --short` shows only the two preserved untracked audit files.