# Changelog — AMNUS

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
