# SPRINT 04 — Agile & Scrum Management

## Objective

Implement the AMNUS Agile addon (`amnus_agile`) on Odoo 19 Community Edition as
the Agile/Scrum planning layer of the platform, without duplicating the standard
`project.task` execution model or the AMNUS deliverable acceptance model.

Reference: `docs/sprints/SPRINT_04_DISCOVERY.md`.

## Deliverables

### Files created

- `addons/amnus/amnus_agile/__init__.py`
- `addons/amnus/amnus_agile/__manifest__.py`
- `addons/amnus/amnus_agile/models/__init__.py`
- `addons/amnus/amnus_agile/models/amnus_agile_user_story.py`
- `addons/amnus/amnus_agile/models/amnus_agile_epic.py`
- `addons/amnus/amnus_agile/models/amnus_agile_sprint.py`
- `addons/amnus/amnus_agile/models/amnus_agile_membership.py`
- `addons/amnus/amnus_agile/models/amnus_agile_burndown.py`
- `addons/amnus/amnus_agile/wizard/__init__.py`
- `addons/amnus/amnus_agile/wizard/amnus_agile_carry_over_wizard.py`
- `addons/amnus/amnus_agile/security/amnus_agile_groups.xml`
- `addons/amnus/amnus_agile/security/amnus_agile_security.xml`
- `addons/amnus/amnus_agile/security/ir.model.access.csv`
- `addons/amnus/amnus_agile/views/amnus_agile_user_story_views.xml`
- `addons/amnus/amnus_agile/views/amnus_agile_epic_views.xml`
- `addons/amnus/amnus_agile/views/amnus_agile_sprint_views.xml`
- `addons/amnus/amnus_agile/views/amnus_agile_carry_over_views.xml`
- `addons/amnus/amnus_agile/views/amnus_agile_reporting_views.xml`
- `addons/amnus/amnus_agile/views/amnus_agile_menus.xml`
- `addons/amnus/amnus_agile/tests/__init__.py`
- `addons/amnus/amnus_agile/tests/common.py`
- `addons/amnus/amnus_agile/tests/test_installation.py`
- `addons/amnus/amnus_agile/tests/test_user_story.py`
- `addons/amnus/amnus_agile/tests/test_epic.py`
- `addons/amnus/amnus_agile/tests/test_sprint.py`
- `addons/amnus/amnus_agile/tests/test_burndown.py`
- `addons/amnus/amnus_agile/tests/test_security.py`
- `addons/amnus/amnus_agile/i18n/amnus_agile.pot`
- `addons/amnus/amnus_agile/i18n/fr_FR.po`
- `addons/amnus/amnus_agile/i18n/ar_SA.po`
- `addons/amnus/amnus_agile/README.md`
- `addons/amnus/amnus_agile/static/description/index.html`
- `docs/technical/amnus_agile.md`
- `docs/sprints/SPRINT_04.md`
- `docs/architecture/ADRs/ADR-004-agile-planning-vs-execution.md`

### Files modified

- `README.md` — `amnus_agile` status updated to implemented
- `CHANGELOG.md` — Sprint 04 implementation entry
- `docs/architecture/addons_architecture.md` — `amnus_agile` status and Sprint 04 decision
- `docs/architecture/dependency_matrix.md` — `amnus_agile` dependency status verified

## Architecture decisions

- **Planning vs. execution separation.** User stories are planning artifacts;
  `project.task` remains the single execution model (stages, assignees,
  deadlines, activities). A story may link to at most one task; the link is
  optional and never carries execution state.
- **Story completion is explicit.** A story becomes `done` only through
  `action_done()`, which requires `in_progress`, non-empty acceptance criteria and
  an AMNUS Agile Manager. Task state never completes a story.
- **Deliverable acceptance is separate.** `amnus.project.deliverable` acceptance
  is contractual and does not drive story completion.
- **Story Points** are Fibonacci values `1, 2, 3, 5, 8, 13, 21`; estimation and
  re-estimation are manager-only.
- **Sprint membership history is a first-class model**
  (`amnus.agile.sprint.membership`). It is append-only from the client
  perspective and written only by server workflows in `sudo`; it records the
  commitment snapshot, the final points, the outcome and the carry-over
  destination.
- **Carry-over is explicit** through `action_carry_over()` and the
  `amnus.agile.carry.over.wizard` transient model, with project/company checks
  and audit logging.
- **Closed sprint metrics are frozen** in `final_*` fields and returned by the
  computed metrics, so later Story Point edits cannot rewrite history. Closed
  sprints cannot be reopened.
- **Burndown is event-based**: rows are created from dated sprint/story events
  only; no synthetic rows are generated for days without an event.
- **No `team_id` model** in this release; sprint capacity is entered manually.
- **Odoo 19 constraint API**: `models.Constraint` is used for the database-level
  uniqueness rules (`(sprint, story)` and `task_id`). The legacy
  `_sql_constraints` attribute is ignored by Odoo 19 and is not used.

## Models

| Model | Type | Purpose |
|-------|------|---------|
| `amnus.agile.user.story` | new | Product backlog user story (planning artifact) |
| `amnus.agile.epic` | new | Project-level grouping of stories with derived progress |
| `amnus.agile.sprint` | new | Time-boxed iteration with lifecycle, metrics, review and retrospective |
| `amnus.agile.sprint.membership` | new | Append-only sprint membership history |
| `amnus.agile.burndown` | new | Dated burndown snapshots |
| `amnus.agile.carry.over.wizard` | new (transient) | Explicit carry-over helper |

Standard models reused: `project.project` (planning container), `project.task`
(execution), `res.company`, `res.users`, `amnus.tag`, `amnus.audit.log`.

### Story lifecycle

```
backlog --Plan--> planned --Start--> in_progress --Done--> done
   |                 |                   |
   +----Cancel-------+-----Cancel--------+--> cancelled
```

Only documented transitions are accepted; backward moves are rejected. Carry-over
is the only path that turns `in_progress` back into `planned`, gated by a context
flag plus manager authorization.

### Sprint lifecycle

```
draft --> planned --> active --> closed
  |          |          |
  +----------+----------+--> cancelled
```

`closed` and `cancelled` are terminal.

## Workflows

### Backlog and planning

- Create/edit stories in the product backlog (manager).
- Plan a story (`action_plan`), start it (`action_start`), complete it
  (`action_done`) or cancel it (`action_cancel`).
- Add a story to a sprint with `action_add_to_sprint` or from the sprint backlog
  tab; a membership row is opened automatically.
- Create the execution task with `action_create_task` (manager-only, one task per
  story).
- Remove a story from a sprint with `action_remove_from_sprint`; the membership
  row is closed as `removed`.

### Sprint execution

- `action_plan()`: draft → planned.
- `action_start()`: planned → active; captures `baseline_points`, refreshes the
  membership commitment snapshots and records the baseline burndown point.
- `action_close()`: active → closed; records the closing burndown point, freezes
  `final_committed_points` / `final_completed_points` /
  `final_carry_over_points`, closes open memberships with `completed`,
  `incomplete` or `cancelled`, and logs an audit event.
- `action_cancel()`: freezes the same figures and closes memberships as
  `cancelled`.
- `action_carry_over(story_ids, target_sprint_id, reason=None)`: moves unfinished
  stories to another sprint of the same project/company, closes the source
  membership as `carried_over` with the destination and reason, and opens a
  membership row in the target sprint.

## Metrics

```
live committed   = Σ story_points where state != cancelled
live completed   = Σ story_points where state == done
live carry-over  = live committed − live completed
membership committed points = story points at commitment (refreshed at sprint start)
membership final points     = story points when the membership ended
velocity (sprint)           = frozen completed points if state == closed, else 0
velocity (selection)        = mean(velocity(sprint)) over the selected closed sprints
```

- `baseline_points`: commitment captured at sprint activation.
- `final_*`: frozen figures captured at closure/cancellation and returned by the
  computed metrics of a closed/cancelled sprint.
- Burndown rows store remaining and completed points per dated event.

## Security

### Groups

| Group | Implies |
|-------|---------|
| `group_amnus_agile_user` | `amnus_core.group_amnus_user`, `amnus_projects.group_amnus_project_user` |
| `group_amnus_agile_manager` | agile user, `amnus_projects.group_amnus_project_manager` |
| `group_amnus_agile_admin` | agile manager |

Groups are never auto-assigned. No standard Odoo or AMNUS group, ACL or record
rule is weakened.

### ACLs

- Agile users: read-only on stories, epics, sprints, membership history and
  burndown.
- Agile managers: CRUD on stories, epics and sprints; CRUD on the transient
  carry-over wizard; read-only on membership history and burndown.
- Agile administrators: same model permissions as managers.

### Record rules

- Multi-company rule on every model (`company_id in company_ids + [False]`).
- Project visibility rule for agile users, mirroring AMNUS project visibility.
- Managers see all records of their allowed companies.
- Membership and burndown rules are read-only for every group.

### Server-side protections

- Manager checks in every workflow action and in the story/sprint `write` guards
  for state, sprint membership and Story Point changes.
- Closed sprints cannot be reopened; metrics are frozen.
- Membership history and burndown are not client-writable.
- Cross-project and cross-company links are rejected by ORM constraints.
- Database-level uniqueness: `unique (sprint_id, story_id)` on membership and
  `unique (task_id)` on stories.
- Audit events are written through `amnus.audit.log._log_event`.

## Views and menus

Under *AMNUS → Agile*:

- **Product Backlog** — list (with drag handle), kanban, form, search.
- **Epics** — list, kanban, form, search.
- **Sprints** — list, kanban, form (Backlog, Review, Retrospective, Burndown,
  Membership History tabs), search, *Carry Over* wizard.
- **Reporting → Burndown** — line graph and read-only list.
- **Reporting → Velocity** — bar graph and read-only list of closed sprints.

All views use Odoo 19 `<list>` syntax. No OWL component and no Enterprise feature
(Gantt, Spreadsheet, dashboards) is used.

## Automated tests

Command:

```
python odoo-bin -c amnus/config/amnus-test.conf -d amnus_test_19 \
  -u amnus_agile --test-enable --test-tags amnus_agile \
  --stop-after-init --log-level=info
```

Result: **60 tests, 0 failed, 0 errors**, process exit code `0`
(`odoo.tests.result: 0 failed, 0 error(s) of 60 tests`).

Breakdown:

- installation / registry / views: 5
- user story lifecycle, constraints, task link, membership protection: 19
- epic progress and guards: 5
- sprint lifecycle, metrics, carry-over, history, review/retrospective: 16
- burndown and velocity: 3
- security groups, ACLs, record rules, company isolation: 12

### Regression

Run in a fully loaded registry through `odoo.tests.shell.run_tests` (the same
harness used in Sprint 03, because isolated `-u <module> --test-enable` registries
are unreliable for user fixture creation):

| Module | Tests | Failures | Errors | Exit |
|--------|------:|---------:|-------:|-----:|
| `amnus_core` | 34 | 0 | 0 | 0 |
| `amnus_crm` | 23 | 0 | 0 | 0 |
| `amnus_projects` | 61 | 0 | 0 | 0 |

No regression was introduced in the existing AMNUS addons.

## Static validation

- All Python files compile (`compileall`).
- All XML files are well-formed.
- The manifest loads; the module installs and upgrades cleanly with
  `--stop-after-init`.

## Internationalization

- `i18n/amnus_agile.pot` — 192 messages exported with
  `odoo-bin i18n export`.
- `i18n/fr_FR.po` — 192/192 translated.
- `i18n/ar_SA.po` — 192/192 translated.
- All user-facing strings are wrapped in `_()`. Arabic RTL layout was not
  visually tested in this sprint.

## Database

- `amnus_test_19` (PostgreSQL 16.14, dedicated test database).
- Modules installed after this sprint: `amnus_core`, `amnus_crm`,
  `amnus_projects`, `amnus_agile`, `project`, `project_todo`, `analytic`,
  `rating`, `uom`, `mail`.
- No core, `amanus_*` legacy module, or production configuration was modified.

## Git

- Branch: `feature/sprint-04-amnus-agile` (from `main` @ `5b324a0`)
- Commit: `feat(amnus_agile): implement Agile and Scrum management`
- Not merged to `main`; branch retained.

## Known limitations

- Burndown is event-based, not a daily snapshot: days without a sprint/story
  event have no row.
- Sprint capacity is manual; no team availability, holiday, timesheet or
  working-hour calculation exists in this release, and no `team_id` model is
  introduced.
- Re-estimating a Story Point value inside an active sprint changes the live
  figures; historical membership snapshots and frozen closure figures preserve
  the audit trail.
- Sprint activation baseline is a single scalar per sprint; per-story originals
  live on membership rows.
- Arabic translations were reviewed for meaning only; visual RTL review was not
  performed.
- Story completion does not automatically close the linked task, and a closed
  task does not complete the story (deliberate separation).

## Readiness for Sprint 05

Ready. `amnus_agile` is installed, tested and documented; the execution model
remains `project.task`, and `amnus_development` can depend on planned stories
through the existing `amnus_core → amnus_projects → amnus_agile` chain.
