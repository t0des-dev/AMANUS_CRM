# Changelog — AMNUS

## Version 19.0.5.1.4 — Sprint 05.1.4 (Dependency & Translation Remediation)

### Fixed
- **F-A05 (undeclared `amnus_agile` dependency):** Resolved via separate optional integration addon `amnus_analysis_agile` that depends on both `amnus_analysis` and `amnus_agile`. Core `amnus_analysis` no longer references `amnus.agile.user.story` and loads successfully without Agile. Story traceability preserved when integration addon is installed.
- **Translation catalog gap:** Regenerated `amnus_analysis.pot` via Odoo `i18n export` (237 entries, up from 164). Rebuilt `fr_FR.po` and `ar_SA.po` from fresh .pot, merging existing translations. All 100 gaps per language filled with French and Arabic translations. 100% coverage (237/237) for both languages. Catalogs validated (Odoo reader + polib + MO compile).
- **Cancellation audit logging:** Added audit event logging to `action_cancel()` in requirement, workshop, and process models. Event created in same transaction as cancellation.

### Added
- Addon `amnus_analysis_agile` (optional integration): depends on `amnus_analysis` and `amnus_agile`. Adds `story_id` field + `_check_story_project` constraint via `_inherit`. Adds view inheritance showing `story_id` in requirement form.
- `docs/sprints/SPRINT_05_1_4_REMEDIATION_REPORT.md` — remediation report.

### Changed
- `amnus_analysis_requirement_views.xml`: removed `story_id` field reference (moved to integration addon).
- `amnus_analysis_requirement.py`: removed `story_id` field, `_check_story_project` constraint, `story_id` from `CONTENT_FIELDS`; added conditional project_id guard; added cancellation audit logging.
- `amnus_analysis_requirement_version.py`: made `story_reference` conditional on field existence.
- `tests/test_requirement.py`: added skip guards for story-related tests when Agile is not installed.

### Notes
- Combined test total: 274 tests (58 analysis + 34 core + 23 crm + 61 projects + 98 agile), 0 failures, 0 errors.
- Reverse-direction traceability guards deferred (cross-module concern, requires changes to `amnus_projects` and `amnus_agile`).
- Visual RTL review not performed (structural assessment only).
- `amnus_analysis_agile` has no test files (story traceability tests are in main addon with skip guards).

---

## Version 19.0.5.1.2 — Sprint 05.1.2 (HIGH Findings Remediation)

### Fixed
- **F-A01 (Rejection reason never captured):** `rejection_reason` is now a writable field; `action_reject()` requires and captures a non-empty rejection reason. Reason is stored in the field and included in the audit event description.
- **F-A02 (No immutable approval snapshot):** New model `amnus.analysis.requirement.version` creates an immutable snapshot on approval, capturing all approved content, related record snapshots (IDs + text names), approval metadata, and company context. Versions are append-only (create requires `env.su`, write/unlink always raise `UserError`). Transactional: if snapshot creation fails, approval rolls back.
- **F-A03 (Protected content freely editable):** `write()` now rejects content field changes on approved/rejected/cancelled records (unless `env.su`). `CONTENT_FIELDS` set defines protected fields. Per-record guard in multi-record writes.
- **F-A04 (Project freely changeable):** `write()` now rejects `project_id` changes on approved/rejected/cancelled records, and when traceability links (task/story/deliverable) exist.
- **F-A06 (Cancellation not manager-restricted):** `action_cancel()` now requires manager authorization for under-review cancellation. Analysts can still cancel their own drafts.
- **F-A07 (Workshop cancel not manager-restricted):** `action_cancel()` on workshops now requires manager authorization.
- **F-A08 (Process cancel not manager-restricted):** `action_cancel()` on processes now requires manager authorization for reviewed processes.
- **F-A09 (Rejection reason not validated):** Fixed via F-A01 — `action_reject()` validates non-empty reason.
- **F-A11 (Revision doesn't clear metadata):** `action_request_revision()` now clears `approved_by`, `approved_date`, `approval_notes`.
- **F-A13 (Cancelled requirements deletable):** `unlink()` now protects cancelled requirements in addition to approved/rejected.
- **F-A18/F-A19 (Metadata clearing, approval notes):** `action_approve()` now sets `approval_notes`; `action_reject()` clears approval metadata; `action_request_revision()` clears both.

### Added
- Model `amnus.analysis.requirement.version` (immutable approval snapshot).
- Fields on `amnus.analysis.requirement`: `approval_notes` (Text), `version_ids` (One2many), `current_version` (Integer). `rejection_reason` changed from readonly to writable.
- Security: ACLs and record rules for version model (read-only for all groups).
- Views: approval_notes and rejection_reason fields (writable) in form view; version history section.
- Tests: 16 new tests (58 total, 0 failures, 0 errors).
- `docs/sprints/SPRINT_05_1_2_REMEDIATION_REPORT.md` — remediation report.

### Changed
- `action_approve()` now creates an immutable version snapshot before returning. Version number = previous + 1.
- `action_reject()` now requires and captures a non-empty rejection reason.
- `action_cancel()` now requires manager authorization for under-review cancellation.
- `write()` now protects content fields and project_id on approved/rejected/cancelled records.
- `unlink()` now protects cancelled requirements.

### Notes
- F-A05 (undeclared `amnus_agile` dependency): documented as optional integration. `story_id` field references `amnus.agile.user.story` which requires `amnus_agile` to be installed. No cycle is created by adding it as a dependency, but the sprint spec prefers optional integration. Known limitation documented.
- F-A15 (source default "other"): deferred — minor data quality issue.
- Audit event for cancellation: not logged (minor gap, deferred).
- New strings ("Approval Notes", version model labels) need i18n catalog regeneration before final merge.
- Combined test total: 274 tests (58 analysis + 34 core + 23 crm + 61 projects + 98 agile), 0 failures, 0 errors.

---

## Version 19.0.5.1.0 — Sprint 05.1 (Requirements Management)

### Added
- `addons/amnus/amnus_analysis` addon (implemented)
  - Manifest: name "AMNUS Analysis", version 19.0.1.0.0, depends `amnus_core`, `amnus_projects`, `project`, `mail`, LGPL-3
  - Model `amnus.analysis.requirement`: dedicated requirement record linked to an implementation project with controlled lifecycle (draft, under review, approved, rejected, cancelled). Fields: reference, name, description, requirement_type (business/functional/non-functional), priority (critical/high/medium/low), business_value, source, acceptance_criteria, notes, project_id, customer_id, stakeholder_id, owner_id, analyst_id, target_stage_id, task_id, story_id, deliverable_id, company_id, approved_by/approved_date, rejected_by/rejected_date/rejection_reason.
  - Model `amnus.analysis.workshop`: structured discovery workshop with reference, type, date/duration, location, facilitator, internal/customer participants, agenda, discussion notes, decisions, outcomes, follow-up actions, related requirements, status.
  - Model `amnus.analysis.process`: AS-IS / TO-BE business process documentation with reference, category, AS-IS/TO-BE descriptions, related requirements, owner, status.
  - Sequence-based references: REQ-00001, WKS-00001, PRC-00001 (native `ir.sequence`, concurrency-safe via `next_by_code`).
  - Workflow actions: `action_submit_for_review`, `action_approve`, `action_reject`, `action_cancel`, `action_request_revision` (requirement); `action_mark_held`, `action_cancel` (workshop); `action_submit_for_review`, `action_approve`, `action_cancel` (process).
  - Security groups: `group_amnus_analysis_user` / `manager` / `admin` (implication hierarchy, never auto-assigned), reusing `amnus_core.group_amnus_user` and `amnus_projects.group_amnus_project_manager`.
  - ACLs in `security/ir.model.access.csv`; record rules in `security/amnus_analysis_security.xml` (multi-company + project visibility + manager sees all).
  - Views: list/kanban/form/search for requirements; list/form/search for workshops and processes; menus under AMNUS → Analysis.
  - Data: `data/amnus_analysis_sequence.xml` (3 sequences).
  - Tests: 42 tests (test_requirement 18, test_workshop 7, test_process 8, test_security 9).
  - README, static description, `fr_FR` and `ar_SA` translations (164 messages each).
- Documentation: `docs/sprints/SPRINT_05_1.md`

### Changed
- `README.md`: `amnus_analysis` status updated to implemented (Sprint 05.1).

### Runtime validation
- `amnus_analysis` installed on `amnus_test_19`: state = installed
- Python compile: OK (all files)
- XML validation: OK (all files well-formed)
- Manifest validation: OK (version 19.0.1.0.0, LGPL-3, depends amnus_core/amnus_projects/project/mail)
- Translation catalogs: Odoo reader + polib + MO compile OK; coverage 100% (fr_FR and ar_SA)
- Automated tests: 42 tests, 0 failures, 0 errors (via Odoo test runner)
- Core regression: 34 tests, 0 failures, 0 errors
- CRM regression: 23 tests, 0 failures, 0 errors
- Projects regression: 61 tests, 0 failures, 0 errors
- Agile regression: 98 tests, 0 failures, 0 errors
- Combined total: 258 tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules and Odoo core untouched

### Notes
- `project.task` remains the single execution model; requirements are planning artifacts that may link to tasks, stories, and deliverables.
- Requirement completion does not complete tasks; task closure does not complete requirements.
- Requirements approval is internal (analyst review + manager approval); portal-based customer approval is out of scope.
- No visual BPMN process designer; process documentation is text-based.
- Arabic translations reviewed for meaning; visual RTL review not performed.
- Not merged to `main` (feature branch `feature/sprint-05-1-amnus-analysis` retained).

---

## Version 19.0.4.5.0 — Sprint 04.5 (P0-A concurrency verification & hardening)

### Fixed
- **Lock-order inversion (RISK-1):** `sprint.action_add_stories` and `sprint.action_carry_over` now lock the affected story rows (sorted) **before** the sprint rows, establishing one global acquisition order `task → story → sprint`. Opposing workflows that previously deadlocked (SQLSTATE `40P01`, demonstrated 10/10 pre-fix by the multi-transaction harness) now serialize with a retryable `40001` (0 deadlocks in 120 post-fix repetitions).
- **Silent post-closure re-estimation (RISK-4):** `amnus.agile.user.story.write` now rejects `story_points` changes when the story's sprint is `closed`/`cancelled` (checked after row locks + invalidation, so a racing closure is always observed). Previously the write silently landed on a finalized sprint.
- **Burndown sequence collision (RISK-5):** `_record_burndown_event` performs a lock-intent row touch on the sprint immediately after its `FOR UPDATE`, converting a concurrent allocator's stale `MAX+1` read from an unhandled unique violation (`23505`) into Odoo's normal retryable serialization failure (`40001`).
- **Task move/link race (C-05b):** `story.write` with `task_id` touches the linked `project_task` row (documented direct SQL, before the story lock) so a concurrent `project.task.write` move serializes against the link and its stale-snapshot guard is retried against committed state instead of silently committing a cross-project move.

### Changed
- Behaviour: re-estimating a story in a closed/cancelled sprint is now rejected with `UserError` (previously allowed with frozen metrics). Tests `test_f01_frozen_metrics_runtime_direct_orm`, `test_f01_closed_sprint_metrics_unchanged_after_later_story_edit` and `test_closed_sprint_metrics_are_frozen` updated to assert the rejection; `docs/technical/amnus_agile.md` reworded.
- Note: PostgreSQL FK `FOR KEY SHARE` already serializes story-link vs task-move in the opposite direction (RISK-3 refuted by evidence — no change needed).

### Added
- `addons/amnus/amnus_agile/tests/concurrency/` — isolated multi-transaction concurrency harness (`harness.py`, `scenarios.py`, `run_concurrency.py`): independent connections/environments per worker, deterministic barrier schedules, PostgreSQL-proven overlap (`pg_stat_activity`/`pg_locks`/`pg_blocking_pids`), faithful emulation of Odoo's bounded service-layer retry (`MAX_TRIES=5` for 40001/40P01/55P03), scenarios C-01…C-06 + S-01/S-01n with invariant checks and residue cleanup. Not imported by `tests/__init__.py` (unaffected by `--test-enable`).
- `docs/sprints/SPRINT_04_5_P0A_CONCURRENCY.md` — full evidence report (pre-fix 110 reps demonstrating defects, post-fix 120 reps all green, overlap/SQLSTATE/deadlock evidence, regressions, residuals).

### Notes
- Pre-fix defects demonstrated on `amnus_test_19`: C-04a 0/10, C-05b 0/10, C-06 0/10, S-01 deadlock 10/10; post-fix: **12/12 scenarios × 10 reps all pass, 0 deadlocks, 0 unique violations, residue all zeros**.
- P0-B fix record: `docs/sprints/SPRINT_04_5_P0B_FIX.md` (commit `37c0bfc`).

### Internationalization (P1 — translation validation)
- Catalogs regenerated via Odoo's own `i18n export` for all four modules (`amnus_core`, `amnus_crm`, `amnus_projects`, `amnus_agile`); `amnus_crm` gained its previously missing `i18n/` directory.
- `amnus_core` PO/POT structurally repaired: entries now carry Odoo-required `#. module:` comments and `#:` occurrences (previously crashed Odoo's `PoFileReader` with `AttributeError` and made `_(…)` silently return source for non-English users).
- `fr_FR.po` / `ar_SA.po` rebuilt per module from the fresh `.pot`, merging prior translations by `msgid`; all 323 remaining empty entries translated (French + Arabic). `amnus_deliverable_id` correctly left untranslated (technical field identifier, not user-facing).
- Every `.po` validated: Odoo `translation_file_reader` parse, `polib` parse, MO compile via `polib.save_as_mofile`, coverage table (agile/core/crm 100%, projects 99.3% — sole gap is the intentional `amnus_deliverable_id`).
- Languages installed in `amnus_test_19` (`fr_FR`, `ar_SA` with `direction='rtl'`) and module terms loaded via `-u amnus_core,amnus_crm,amnus_projects,amnus_agile` (never `-u all`).
- DB verified: jsonb translation values present for sample menus/models/fields in both `fr_FR` and `ar_SA`; `res.lang ar_SA direction='rtl'`; no custom OWL/CSS/asset bundles in any module (only `static/description/index.html`), so Odoo web-client RTL applies unbroken.
- Sequential regressions re-run green after i18n: core 34, crm 23, projects 61, agile 98 — all `0 failed, 0 error(s)`, exit 0.
- Evidence report: `docs/sprints/SPRINT_04_5_P1_I18N.md`.

## Version 19.0.4.1.0 — Sprint 04.2 (Agile Security & Data Integrity Remediation)

### Fixed
- Sprint lifecycle/state and frozen snapshot fields (`baseline_points`, `final_*`) protected from direct ORM/RPC create/write; workflow-only internal transitions with row locking and atomic closure/cancel/start side effects.
- Sprint/story create/unlink guards prevent fabricated closed/done records, assignment to closed/cancelled sprints, and deletion of historical sprint/membership/burndown records.
- Story/Task integrity: linked tasks cannot be moved across project/company; `task_state`/`task_user_ids` computed access-safely without sudo disclosure.
- Carry-over rejected from closed/cancelled source sprints and cannot rewrite closed membership history; membership re-entry into same sprint rejected to preserve append-only history.
- Burndown converted to append-only dated events (baseline, scope add/remove, re-estimation, start, completion, carry-over, cancellation, closure) with deterministic ordering and continuous carry-forward series.
- Story direct state writes rejected; workflow actions enforce completion criteria, audit logging and burndown side effects. Epic state writes guarded.
- Burndown project-visibility record rule added for agile users; negative sprint capacity rejected.

### Added
- `addons/amnus/amnus_agile/tests/test_remediation.py` regression coverage for audit findings F-01–F-16 and Day 1–5 burndown scenario.
- `docs/sprints/SPRINT_04_2_REMEDIATION.md` mapping findings to changes/tests.

### Notes
- `docs/sprints/SPRINT_04_1_AUDIT.md` preserved unchanged. Fresh independent re-audit required.

## Version 19.0.4.0.0 — Sprint 04 (Agile & Scrum Management)

### Added
- `addons/amnus/amnus_agile` addon (implemented)
  - Manifest: name "AMNUS Agile", version 19.0.1.0.0, depends `amnus_core`, `amnus_projects`,
    `project`, `mail`, LGPL-3
  - Model `amnus.agile.user.story`: product backlog planning artifact (title, description,
    business value, acceptance criteria, priority, sequence, Fibonacci Story Points, epic,
    sprint, optional task link, AMNUS tags); read-only `task_state` / `task_user_ids`
  - Model `amnus.agile.epic`: project-level story grouping with derived
    `story_count`, `completed_story_count` and `progress`
  - Model `amnus.agile.sprint`: lifecycle (`draft`, `planned`, `active`, `closed`,
    `cancelled`), backlog, manual capacity, live metrics, frozen closure metrics,
    structured review and retrospective, structured improvement actions
  - Model `amnus.agile.sprint.membership`: append-only sprint membership history with
    commitment snapshot, final points, outcome, carry-over destination and reason
  - Model `amnus.agile.burndown`: dated burndown points recorded from sprint/story events
  - Transient model `amnus.agile.carry.over.wizard` and explicit
    `action_carry_over()` with project/company checks and audit logging
  - Story workflow `action_plan` / `action_start` / `action_done` / `action_cancel`,
    `action_add_to_sprint` / `action_remove_from_sprint`, `action_create_task`
  - Sprint workflow `action_plan` / `action_start` / `action_close` / `action_cancel`,
    baseline commitment, frozen `final_*` metrics, no reopening of closed sprints
  - Velocity: per-sprint `velocity_points` from frozen completed points and
    `_get_sprint_velocity()` mean over closed sprints
  - Manager-only Story Point estimation and planning-state changes, enforced in `write()`
  - Database uniqueness via Odoo 19 `models.Constraint`:
    `unique (sprint_id, story_id)` on membership and `unique (task_id)` on stories
  - Security: `group_amnus_agile_user`, `group_amnus_agile_manager`,
    `group_amnus_agile_admin` (hierarchy, never auto-assigned), ACLs and record rules;
    membership history and burndown are client read-only and written only by server workflows
  - Views: product backlog list/kanban/form/search, epic list/kanban/form/search,
    sprint list/kanban/form/search (Backlog, Review, Retrospective, Burndown and
    Membership History tabs), carry-over wizard, burndown line graph/list and
    closed-sprint velocity bar graph/list, AMNUS Agile menus and reporting menu
  - Audit events on story state changes, sprint lifecycle, backlog updates, carry-over
    and task link creation
  - Automated tests: 60 at_install tests (installation, user story, epic, sprint,
    burndown/velocity, security)
  - README, static description, `fr_FR` and `ar_SA` translations (192 messages each)
- Documentation: `docs/technical/amnus_agile.md`, `docs/sprints/SPRINT_04.md`,
  `docs/architecture/ADRs/ADR-004-agile-planning-vs-execution.md`
- Discovery record retained: `docs/sprints/SPRINT_04_DISCOVERY.md`

### Changed
- `README.md`: `amnus_agile` status updated to implemented
- `docs/architecture/dependency_matrix.md`: `amnus_agile` status updated; `project`/`mail`
  dependencies verified
- `docs/architecture/addons_architecture.md`: `amnus_agile` status and Sprint 04 decision updated

### Runtime validation
- `amnus_agile` installed and upgraded on `amnus_test_19`
- Python compile: OK
- XML validation: OK (all files well-formed)
- Manifest validation: OK
- Automated tests: 60 at_install tests, 0 failures, 0 errors
- `amnus_core` regression: 34 at_install tests, 0 failures, 0 errors
- `amnus_crm` regression: 23 at_install tests, 0 failures, 0 errors
- `amnus_projects` regression: 61 at_install tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules and Odoo core untouched

### Notes
- `project.task` remains the single execution model; stories are planning artifacts
  (see ADR-004)
- Story completion requires `in_progress`, non-empty acceptance criteria and an Agile
  Manager; task state never completes a story and deliverable acceptance is separate
- Closed/cancelled sprint metrics are frozen and cannot be rewritten by later Story
  Point edits; closed sprints cannot be reopened
- Sprint capacity is manual; no team/availability model exists in this release
- Burndown is event-based: days without a sprint/story event have no row
- Arabic translations reviewed for meaning; visual RTL review not performed
- Not merged to `main`; branch `feature/sprint-04-amnus-agile` retained


## Version 19.0.3.0.0 — Sprint 03 (Projects & Project Lifecycle)

### Added
- `addons/amnus/amnus_projects` addon (implemented)
  - Manifest: name "AMNUS Projects", version 19.0.1.0.0, depends `amnus_core`, `amnus_crm`, `project`, `mail`, LGPL-3
  - `project.project` extension: AMNUS project flag, implementation request link, stored request type,
    actual go-live, deliverables, deliverable count, AMNUS tags
  - SQL constraint `UNIQUE (amnus_request_id)` — one project per implementation request
  - `project.task` extension: optional deliverable link with same-project validation
  - Model `amnus.project.deliverable`: contractual deliverable with a controlled
    submit / accept / reject / reset-to-draft workflow
  - `amnus.crm.project.request` extension: `project_id`, `project_count`,
    `action_create_project()` (approved requests only, manager-only, company-consistent,
    row-locked, duplicate-safe) and `action_view_project()`
  - Security: `group_amnus_project_user`, `group_amnus_project_manager`,
    `group_amnus_project_admin` (hierarchy, never auto-assigned), ACLs and record rules
  - Views: project form/search, task form/search, deliverable list/form/search,
    CRM request handover buttons/search, AMNUS Projects menus
  - Audit events on every deliverable transition and on project handover
  - Automated tests: 61 at_install tests (installation, project integration, CRM handover,
    deliverables, task integration, security)
  - README, static description, `fr_FR` and `ar_SA` translations
- Documentation: `docs/technical/amnus_projects.md`, `docs/sprints/SPRINT_03.md`,
  `docs/architecture/ADRs/ADR-003-project-lifecycle-and-deliverables.md`
- Discovery record retained: `docs/sprints/SPRINT_03_DISCOVERY.md`

### Changed
- `README.md`: `amnus_projects` status updated to implemented
- `docs/architecture/dependency_matrix.md`: `amnus_projects` status updated; `project`
  dependency verified and installed in `amnus_test_19`
- `docs/architecture/addons_architecture.md`: `amnus_projects` status and shared-model note updated

### Runtime validation
- `amnus_projects` installed on `amnus_test_19`: state = installed
- Newly installed dependency modules: `project`, `project_todo`, `analytic`, `rating`, `uom`
- `sale`, `account` and `hr_timesheet` remain uninstalled
- Python compile: OK
- XML validation: OK (all files well-formed)
- Manifest validation: OK
- Automated tests: 61 at_install tests, 0 failures, 0 errors
- `amnus_core` regression: 34 at_install tests, 0 failures, 0 errors
  (run in a fully loaded registry via `odoo.tests.shell.run_tests`)
- `amnus_crm` regression: 23 at_install tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules untouched; `amnus_core` manifest unchanged

### Notes
- Standard project/task/stage/state/health models are reused; no duplicate lifecycle models
- `sale` is intentionally not a dependency
- The addon ships no stage data (recommended stage mapping documented)
- Test-runner caveat: `-u amnus_core --test-enable` builds an isolated registry without
  `mail`/`calendar` while the database schema keeps their NOT NULL columns, so user creation
  fails in that isolated run. This is a pre-existing harness limitation, not a
  `amnus_projects` regression; the suite passes in a fully loaded registry.
- Not merged to `main`; Sprint 04 intentionally not started


## Version 19.0.2.0.0 — Sprint 02 (CRM & Customer Relationship Management)

### Added
- `addons/amnus/amnus_crm` addon (implemented)
  - Manifest: name "AMNUS CRM", version 19.0.1.0.0, depends `amnus_core`, `crm`, `contacts`, `mail`, LGPL-3
  - `crm.lead` extension: AMNUS implementation flag, request type, project summary, current system, expected dates, estimated users, company size, technical notes, AMNUS tags
  - Model `amnus.crm.project.request`: structured implementation request with controlled workflow
  - Sequence: `AMNUS-CRM-YYYY-XXXX` for request references
  - Security: ACLs (CSV) + company isolation record rules
  - Views: CRM lead form/search inheritance, request list/form/search, AMNUS CRM menu
  - Automated tests: 23 at_install tests (installation, lead fields, project requests, security)
  - README, static description
- Documentation: `docs/technical/amnus_crm.md`, `docs/sprints/SPRINT_02.md`

### Changed
- README.md: `amnus_crm` status updated to implemented
- CHANGELOG.md: Sprint 02 entry added

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running
- Test database: `amnus_test_19`

### Runtime validation
- `amnus_crm` installed on `amnus_test_19`: state = installed
- Python compile: OK
- XML validation: OK (all files well-formed)
- Manifest validation: OK
- Automated tests: 23 at_install tests, 0 failures, 0 errors
- `amnus_core` regression: 34 at_install tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules untouched

## Version 19.0.1.1.0 — Sprint 01.1 (Core Runtime Validation & Security Hardening)

### Changed
- Manifest: added `base_setup` dependency (required for settings view inheritance)
- `amnus.tag`: replaced `_sql_constraints` with `models.Constraint` (Odoo 19 convention)
- `amnus.tag`: NULL-safe uniqueness constraint (global tags + company-specific tags)
- `amnus.audit.log`: renamed `log_event()` → `_log_event()` (non-RPC-callable)
- `amnus.audit.log`: identity (user/company) now derived from environment (not forgeable)
- `amnus.tag` and `amnus.audit.log`: added company isolation record rules
- `security.xml`: reorganized (groups before ACLs), removed `category_id` (not available in Odoo 19 `res.groups`)
- ACLs moved from CSV to XML for proper load ordering
- Views: `<tree>` → `<list>` (Odoo 19 view type name)
- Views: settings xpath updated to Odoo 19 pattern (`//form` with `<app>`/`<block>`/`<setting>`)
- `amnus_menus.xml`: `target="inline"` → `target="new"` (valid Odoo 19 value)
- Tests: expanded with global/company uniqueness, cross-company access, audit API protection, config persistence, menu visibility, security group inheritance
- Tests: `groups_id` → `group_ids` (Odoo 19 field name), `tree` → `list`
- i18n: added `amnus_core.pot`, `fr_FR.po`, `ar_SA.po`

### Fixed
- `_sql_constraints` no longer supported in Odoo 19 → `models.Constraint`
- `base_setup` dependency missing → added
- `category_id` field not on `res.groups` in Odoo 19 → removed
- `ir.model.access.csv` processed before groups defined → moved ACLs to XML
- `log_event()` RPC-callable → renamed to `_log_event()`
- Tag uniqueness not NULL-safe → added ORM constraint
- No record rules for multi-company → added company isolation rules
- `tree` view type invalid in Odoo 19 → changed to `list`

### Runtime validation
- Database: `amnus_test_19` created (PostgreSQL 16.14, owned by `amanus`, UTF8)
- Module installed: `amnus_core` state = installed
- Tests: 34 at_install tests, 0 failures, 0 errors
- All Python files compile, all XML files valid

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running

## Version 19.0.1.0.0 — Sprint 01 (Core Foundation)

### Added
- `addons/amnus/amnus_core` addon (implemented)
  - Manifest: name "AMNUS Core", version 19.0.1.0.0, depends `base`, LGPL-3
  - Model `amnus.tag` (reusable tags): name, color, active, category, description, company_id
  - Model `amnus.audit.log` (immutable audit log): name, date, user_id, model_name, record_id, action, description, company_id
  - `res.config.settings` extension: AMNUS Enabled, Audit Logging Enabled
  - Security groups: AMNUS User, AMNUS Manager, AMNUS Administrator (implication hierarchy)
  - ACLs in `security/ir.model.access.csv`
  - Menus and views: tags list/form/search, audit logs list/form/search, settings, AMNUS root menu
  - Automated tests: test_amnus_tag, test_amnus_audit_log, test_security
  - Static description, README
- `config/amnus-dev.conf.example` (development configuration sample)
- Documentation: ADR-001, ADR-002, docs/technical/amnus_core.md, docs/sprints/SPRINT_01.md

### Changed
- README.md, CHANGELOG.md, dependency matrix, addons architecture updated to reflect `amnus_core` implementation

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running

### Notes
- `amnus_core` not yet installed against a database (pending dedicated test database approval).
- No existing `amanus_*` module or database was modified.

## Version 19.0.0.0.0 — Sprint 00 (Foundation & Documentation)

### Added
- Repository structure (AGENTS.md, README.md, CHANGELOG.md, LICENSE, docs/, config/, requirements/, scripts/, tests/)
- `addons/amnus/` container for future `amnus_*` addons (empty — no business modules yet)
- `docs/architecture/system_architecture.md`
- `docs/architecture/addons_architecture.md`
- `docs/architecture/dependency_matrix.md`
- `docs/technical/development_standards.md`
- `docs/technical/environment_setup.md`
- `docs/technical/security_standards.md`
- `docs/sprints/SPRINT_00.md`
- `AGENTS.md` with permanent development rules

### Environment discovered & verified (read-only)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running
- Existing `custom_addons` ecosystem (`amanus_*` prefix) — no `amnus_` naming conflict
- No existing Git repository; one to be initialized for AMNUS

### Changed
- None

### Removed
- None

### Notes
- No business functionality implemented in this Sprint.
- No existing database, configuration, or custom addon was modified.
