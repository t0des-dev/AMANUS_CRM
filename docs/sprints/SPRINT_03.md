# SPRINT 03 — Projects & Project Lifecycle

## Objective

Implement the AMNUS Projects addon (`amnus_projects`) on Odoo 19 Community
Edition, extending standard Project and connecting the approved CRM
implementation request to the project lifecycle.

Reference: `docs/sprints/SPRINT_03_DISCOVERY.md`.

## Deliverables

### Files created

- `addons/amnus/amnus_projects/__init__.py`
- `addons/amnus/amnus_projects/__manifest__.py`
- `addons/amnus/amnus_projects/models/__init__.py`
- `addons/amnus/amnus_projects/models/project_project.py`
- `addons/amnus/amnus_projects/models/project_task.py`
- `addons/amnus/amnus_projects/models/amnus_project_deliverable.py`
- `addons/amnus/amnus_projects/models/amnus_crm_project_request.py`
- `addons/amnus/amnus_projects/security/amnus_projects_groups.xml`
- `addons/amnus/amnus_projects/security/amnus_projects_security.xml`
- `addons/amnus/amnus_projects/security/ir.model.access.csv`
- `addons/amnus/amnus_projects/views/project_project_views.xml`
- `addons/amnus/amnus_projects/views/project_task_views.xml`
- `addons/amnus/amnus_projects/views/amnus_project_deliverable_views.xml`
- `addons/amnus/amnus_projects/views/amnus_crm_project_request_views.xml`
- `addons/amnus/amnus_projects/views/amnus_projects_menus.xml`
- `addons/amnus/amnus_projects/tests/__init__.py`
- `addons/amnus/amnus_projects/tests/common.py`
- `addons/amnus/amnus_projects/tests/test_installation.py`
- `addons/amnus/amnus_projects/tests/test_project_integration.py`
- `addons/amnus/amnus_projects/tests/test_crm_handover.py`
- `addons/amnus/amnus_projects/tests/test_deliverables.py`
- `addons/amnus/amnus_projects/tests/test_task_integration.py`
- `addons/amnus/amnus_projects/tests/test_security.py`
- `addons/amnus/amnus_projects/static/description/index.html`
- `addons/amnus/amnus_projects/README.md`
- `addons/amnus/amnus_projects/i18n/amnus_projects.pot`
- `addons/amnus/amnus_projects/i18n/fr_FR.po`
- `addons/amnus/amnus_projects/i18n/ar_SA.po`
- `docs/technical/amnus_projects.md`
- `docs/sprints/SPRINT_03.md`
- `docs/architecture/ADRs/ADR-003-project-lifecycle-and-deliverables.md`

### Files modified

- `README.md` — `amnus_projects` status updated to implemented
- `CHANGELOG.md` — Sprint 03 implementation entry
- `docs/architecture/dependency_matrix.md` — `amnus_projects` status, verified `project` dependency
- `docs/architecture/addons_architecture.md` — `amnus_projects` status, shared-model note

## Architecture decisions

- **Reuse, do not replace.** `project.project`, `project.task`,
  `project.project.stage`, `project.task.type`, task states and
  `last_update_status` remain the single source of truth.
- **One new business model only:** `amnus.project.deliverable`. No Scrum, Agile,
  QA, DevOps or Timesheets models.
- **Planned dates reuse standard fields:** planned start → `date_start`, planned
  go-live/end → `date`, actual go-live → `amnus_actual_go_live`.
- **Request link is authoritative on the project** (`project.project.amnus_request_id`,
  SQL UNIQUE), with a backlink on the request validated by a constraint.
- **Handover is concurrency-safe** through a row lock plus the unique constraint,
  without manual commit.
- **Deliverable workflow is server-authoritative.** Direct state/sign-off writes are
  rejected outside the workflow methods; accepted records are immutable and
  undeletable for non-managers.
- **No stage data shipped.** Stage names are an operational configuration concern;
  a recommended mapping is documented in the addon README.
- **New project security groups** imply standard Odoo project groups; no standard
  group, ACL or record rule is modified or weakened, and no group is auto-assigned.
- **No `sale` dependency**; `mail` is declared explicitly for chatter.

## Models and fields

See `docs/technical/amnus_projects.md` for the complete field and method reference.

Summary:

- `project.project`: `amnus_is_amnus_project`, `amnus_request_id`,
  `amnus_request_type`, `amnus_actual_go_live`, `amnus_deliverable_ids`,
  `amnus_deliverable_count`, `amnus_tag_ids`.
- `project.task`: `amnus_deliverable_id` with same-project constraint.
- `amnus.project.deliverable`: new model with acceptance workflow.
- `amnus.crm.project.request`: `project_id`, `project_count`,
  `action_create_project()`, `action_view_project()`.

## Workflow

```
CRM request: draft → submitted → reviewed → approved
                                             │
                                             ▼ (manager, approved, unlinked)
                                    project.project (AMNUS)
                                             │
                                             ▼
Deliverable: draft → submitted → accepted
                        └─────→ rejected → draft
```

Every deliverable transition records the acting user and a UTC timestamp and
writes an `amnus.audit.log` event. Rejection requires a written reason.

## Security

- Groups: `group_amnus_project_user`, `group_amnus_project_manager`,
  `group_amnus_project_admin` (hierarchy: user → manager → admin).
- ACLs in `security/ir.model.access.csv`.
- Record rules: deliverable multi-company, project visibility and manager all-rule.
- Handover and deliverable transitions authorized server-side; direct RPC writes
  to protected fields blocked.
- Company consistency includes partner hierarchy (child contacts resolved through
  their commercial entity).

## Automated tests

- **61 tests, 0 failures, 0 errors** (`amnus_projects`, `at_install`).
- Breakdown: installation 6, project integration 9, CRM handover 10,
  deliverables 20, task integration 6, security 10.
- Coverage includes installation, project/task integration, handover guards and
  concurrency defenses, deliverable workflow and immutability, security groups,
  company isolation and forged-field protection.

### Regression

- `amnus_core`: 34 tests, 0 failures, 0 errors — run in a fully loaded registry
  via `odoo.tests.shell.run_tests`.
- `amnus_crm`: 23 tests, 0 failures, 0 errors.

A known harness caveat is documented: running `-u amnus_core --test-enable`
builds an isolated registry (only `amnus_core` and its declared dependencies)
while the database schema still contains columns managed by `mail`/`calendar`.
User creation in that isolated registry therefore fails on NOT NULL columns that
are not part of its registry. This is a pre-existing test-runner limitation, not
an `amnus_projects` regression; the suite passes in a fully loaded registry.

## Database

- `amnus_test_19` (PostgreSQL 16.14, dedicated test database).
- Newly installed modules: `project`, `project_todo`, `analytic`, `rating`, `uom`.
- `sale`, `account` and `hr_timesheet` remain uninstalled.
- Module states after delivery: `amnus_core`, `amnus_crm`, `amnus_projects`,
  `project` = installed.

## Static validation

- All Python files compile.
- All XML files are well-formed.
- Manifest loads and the module installs/upgrades cleanly with `--stop-after-init`.

## Git

- Branch: `feature/sprint-03-amnus-projects`
- Commit: `feat(amnus_projects): implement AMNUS project lifecycle`
- Not merged to `main`.

## Known limitations

- No stage data is shipped (deliberate; recommended mapping documented).
- No chatter on the CRM request; the handover posts on the project.
- Deliverables are not linked to `project.milestone`.
- Cancelling a request after handover does not cancel/delete the project.
- One actual go-live date per project, not per deliverable.

## Readiness for Sprint 04

Ready. Sprint 03 is complete; Sprint 04 is intentionally not started in this
change set.
