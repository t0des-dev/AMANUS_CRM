# SPRINT 03.1 — Independent Integration Audit & Safe Git Merge

Date: 2026-11-14
Auditor: Independent code review (senior Odoo 19 architect / security / QA)
Branch audited: `feature/sprint-03-amnus-projects`
Implementation commit: `6d2b56d` — `feat(amnus_projects): implement AMNUS project lifecycle`
Integration base: `main` @ `fa32ccc`

## 1. Phase 1 — Git verification

| Check | Result |
|---|---|
| Current branch | `feature/sprint-03-amnus-projects` |
| Working tree | clean (no unstaged / untracked leftovers) |
| HEAD | `6d2b56d` |
| Ancestry | `main` (`fa32ccc`) is an ancestor of the feature branch |
| Sprint 03 diff vs base (`fa32ccc..6d2b56d`) | 37 files, +6000 / −20 — addon, tests, docs only |
| Unexpected modifications | none |

No overwrite / discard performed.

## 2. Phase 2 — Security audit

| Area | Finding | Severity | Verdict |
|---|---|---|---|
| CRM handover authorization | `action_create_project` requires `amnus_projects.group_amnus_project_manager` or superuser before any state work | — | OK |
| Handover state guard | approved-only + not-already-linked, re-checked under `SELECT … FOR UPDATE` | — | OK |
| Concurrency | row lock + DB unique constraint `UNIQUE (amnus_request_id)` | — | OK |
| Transaction atomicity | no manual `commit()`; audit + message post inside same transaction; rollback covered by test | — | OK |
| Company consistency | request / opportunity / customer / project checked; child contacts resolved through `commercial_partner_id` | — | OK |
| Deliverable workflow | state/sign-off writes guarded by `env.su`; transitions authorize then use `sudo().write()`; identities from `env.user`, timestamps from `Datetime.now()` | — | OK |
| Rejection | mandatory non-empty reason | — | OK |
| Post-acceptance | accepted deliverables immutable for non-managers; cannot be unlinked/deleted; project with accepted deliverables cannot be deleted | — | OK |
| ORM/RPC guards | `project.amnus_request_id` and `request.project_id` writes blocked for non-superuser; constraints enforced server-side | — | OK |
| Record rules / ACLs | dedicated groups; deliverable ACLs (user/manager/admin); record rules (company, visibility, manager) | — | OK |
| sudo usage | narrowly scoped (internal handover backlink + workflow transitions after explicit authorization checks) | — | OK |
| Multi-record operations | transitions validate all records in loops before `sudo().write()` | — | OK |
| Bypasses missed by happy-path tests | none found in code review; negative-path coverage present (unapproved, unauthorized, duplicate, mismatch, forged link, failed audit rollback) | — | OK |

**Security verdict: no critical findings.**

## 3. Phase 3 — Regression test audit

Commands executed and results:

| Suite | Command | Result |
|---|---|---|
| `amnus_projects` | `odoo-bin -c …\config\amnus-test.conf -d amnus_test_19 -u amnus_projects --test-enable --test-tags amnus_projects --stop-after-init` | **61 tests, 0 failed, 0 errors** (exit 0) |
| `amnus_core` | `run_tests(env, "amnus_core", modules=["amnus_core"])` via `odoo shell` (fully loaded registry) | **34 tests, 0 failed, 0 errors** (exit 0, `success=True`) |
| `amnus_crm` | `odoo-bin -c … -d amnus_test_19 -u amnus_crm --test-enable --test-tags amnus_crm --stop-after-init` | **23 tests, 0 failed, 0 errors** (exit 0) |

### Core test harness limitation (investigation outcome)

- Isolated `-u amnus_core --test-enable` runs fail with:
  `null value in column "notification_type" of relation "res_users" violates not-null constraint`
  and a follow-up `null value in column "calendar_default_privacy" of relation "res_users_settings"`.
- Root cause: the test registry is built from the module dependency closure. `amnus_core` declares only `base` + `base_setup`, so during a test run of `amnus_core` the `mail` and `calendar` models are absent from the registry, even though the database schema was installed with them present (they are real installed modules in the DB). `res.users.notification_type` and `res.users_settings.calendar_default_privacy` are therefore NOT NULL columns without ORM-declared defaults in that registry, and `BaseModel._add_missing_default_values` has no field to apply → raw INSERT fails.
- Verified through temporary diagnostic probes (registry module set, field presence, defaults, `_add_missing_default_values`) and by adding `mail` to the dependency closure, which moved the failure to `calendar_default_privacy` — confirming an isolated-registry/installed-schema mismatch rather than an addon bug.
- Remediation: run the Core suite in a **fully loaded registry** via the programmatic runner (`odoo.tests.shell.run_tests`) → green (34/34).
- This is a pre-existing Odoo test-runner harness limitation, not an `amnus_projects` regression.

## 4. Phase 4 — Odoo 19 compatibility

| Area | Check | Result |
|---|---|---|
| Models | `models.Constraint`, `Many2one`, `One2many` inverses, `related` stored readonly, Selection | OK |
| ORM methods | create/write/unlink overrides, `_check` methods, workflow methods | OK |
| Constraints | ORM-level `@api.constrains` and `models.Constraint` UNIQUE | OK |
| Security APIs | groups `implied_ids`, record rules, ACLs, `env.su`, `has_group` | OK |
| XML views | `<list>`, `<statusbar>`, buttons, groups, domains, `<tree>`-free | OK |
| Manifest | depends `amnus_core`, `amnus_crm`, `project`, `mail`; LGPL-3; installable | OK |
| Test APIs | `TransactionCase`, `with_user`, `assertRaises`, savepoints | OK |
| Deprecated / removed APIs | none used | OK |

Odoo 19 specifics confirmed against source: `%s` placeholder style with psycopg2 tuple params, `<list>` view type, `models.Constraint`, `mail.thread` for deliverables.

## 5. Phase 5 — Documentation

- Created: `docs/sprints/SPRINT_03_1_AUDIT.md` (this document).
- Prior sprint artifacts updated: `docs/technical/amnus_projects.md`, `docs/sprints/SPRINT_03.md`, `CHANGELOG.md`, architecture docs.

## 6. Phase 6 — Merge decision

Preconditions at audit time:

1. Feature branch working tree: **clean** ✓
2. Main HEAD before integration: `fa32ccc` ✓ (still expected unchanged until merge)
3. Critical checks: implementation clean, tests green, security findings none, compatibility OK

**Decision: APPROVED FOR MERGE.**

Remaining risks (non-blocking):

- Isolated-registry test limitation for `amnus_core` remains a known Odoo harness caveat (mitigated by fully-loaded-registry runs).
- Deliverables vs. `project.milestone` linkage deferred to a future sprint by design.

## Final report references

- Test counts: amnus_projects 61/61, amnus_core 34/34, amnus_crm 23/23 — all green.
- Final merge commit on feature branch: pending this audit document.
