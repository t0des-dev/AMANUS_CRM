# SPRINT 04 — DISCOVERY: Agile & Scrum Management Architecture

## 1. Executive summary

AMNUS now owns the full lifecycle of an Odoo implementation project:

```
CRM opportunity → approved implementation request → AMNUS project → deliverables → tasks → Agile/QA/DevOps/Timesheets
```

Sprint 04 designs the **Agile & Scrum management** layer on top of that chain, reusing
the standard Odoo 19 `project.task` execution model and the AMNUS deliverable acceptance
state. The design must not duplicate task models, stages or states.

## 2. Verified findings (Odoo 19 Community source, read-only inspection)

### 2.1 `project.task` (verified)

- Name: `project.task`; abstract mixins: `portal.mixin`, `mail.thread.cc`, `mail.activity.mixin`,
  `rating.mixin`, `mail.tracking.duration.mixin`, `html.field.history.mixin`.
- `_mail_post_access = 'read'`, `_mail_thread_customer = True`.
- `_order = "priority desc, sequence, date_deadline asc, id desc"`.
- Fields: `name` (Title, required), `description` (Html), `priority` (0 Low / 1 Medium / 2 High / 3 Urgent),
  `sequence`, `stage_id` (Many2one `project.task.type`, computed+stored, default from context, group expand),
  `tag_ids` (M2M `project.tags`), `state` (open + closed), `is_closed` (computed),
  `date_deadline`, `user_ids` (M2M `res.users`, `project_task_user_rel`), `milestone_id`.
- States: open — `01_in_progress`, `02_changes_requested`, `03_approved`, `04_waiting_normal`;
  closed — `1_done` (Done), `1_canceled` (Cancelled). Closed states are defined by `CLOSED_STATES`.
- Dependencies: `allow_task_dependencies` (related `project_id`), `depend_on_ids` (M2M, "blocked by"),
  `dependent_ids` (M2M, "blocks"), relation `task_dependencies_rel`; auto state transitions on write
  (blocked → `04_waiting_normal`, unblocked → `01_in_progress`).
- Rating drives task state (`03_approved` when rating satisfied, else `02_changes_requested`).
- Working time / tracking mixins attached to `stage_id`.

### 2.2 `mail.activity.mixin` (verified)

- `activity_ids` One2many toward `mail.activity` (via `res_id` / `res_model`).
- Computeds: activity state, activity user (`activity_user_id`), deadline, summary, exception decoration/icon,
  `my_activity_date_deadline`, last activity state (SQL: planned / overdue / today).
- Kanban widget: `kanban_activity`; scheduling actions: reschedule today / tomorrow / next week.

### 2.3 `amnus.project.deliverable` (verified, Sprint 03)

- States: `draft`, `submitted`, `accepted`, `rejected`.
- Sign-off: submitter/acceptor identity + timestamps; rejection reason mandatory; accepted immutable.
- One2many `task_ids` via task inverse `amnus_deliverable_id` (execution traceability).

### 2.4 AMNUS security / core context (verified)

- Groups: `group_amnus_user`, `group_amnus_manager`, `group_amnus_admin` (`amnus_core`, `noupdate=1`), plus
  `group_amnus_project_user`, `group_amnus_project_manager`, `group_amnus_project_admin` (`amnus_projects`).
- `amnus_core`: `amnus.tag`, `amnus.audit.log` (internal `_log_event`), `res.config.settings`, AMNUS menu.
- `amnus_crm`: `amnus.crm.project.request` (draft/submitted/reviewed/approved/rejected/cancelled) with
  `action_create_project` handover.
- `project` ACLs: `project.group_project_user` (read-only on projects), `project.group_project_manager` (CRUD),
  `project.group_project_stages`; task visibility via standard rules.

## 3. Proposed models (design for `amnus_agile` — not implemented in this sprint)

### 3.1 Product Backlog

Recommendation: user stories live in dedicated `amnus.agile.*` records and trace to `project.task`; no duplicate task model.

- `amnus.agile.user.story` — `name`, `description`, `acceptance_criteria` (Text), `business_value` (Text),
  `priority` (reuse task-like scale or explicit), `story_points` (Integer/Float), `epic_id` (M2O epic, optional),
  `task_id` (M2O `project.task`, optional; same-project validated), `state` (draft/planned/in_progress/done),
  `company_id` (company isolation), `tag_ids` (M2M `amnus.tag`).
- `amnus.agile.epic` — `name`, `description`, `project_id` (M2O `project.project`), `child_story_ids`
  (M2M user stories / parent-child grouping), state.

### 3.2 Sprint Management

- `amnus.agile.sprint` — `name`, `project_id` (M2O project), `start_date`, `end_date`, `goal` (Text),
  `state` (planned/in_progress/done), `item_ids` (M2M user stories — sprint backlog), `company_id`.
- Sprint planning / review / retrospective: notes fields and state transitions on the sprint
  (planning notes, review notes, retrospective notes); or wizards. Keep simple: state machine + notes.

### 3.3 Open design decisions

1. User stories: independent backlog records linked to `project.task` (recommended) vs. fields extended onto
   `project.task` directly. Recommendation: independent records (`amnus.agile.user.story`) to preserve the
   "no duplicate task model" rule and keep execution (`project.task`) clean.
2. Story points scale: Fibonacci (1/2/3/5/8/…) vs. custom — decision pending product input.
3. Sprint capacity: planned capacity computed from team member availability over sprint date range; needs
   `res.users`/`hr` team data — out of scope for pure-Community design; recommend deriving from assigned users.
4. Burndown source: effort points over time vs. activity/deadline based — must be decided.
5. Velocity: computed from completed sprint points (sprint state `done`).

## 4. Workflow definitions (proposed)

```
backlog item: draft → planned → in_progress → done (or canceled)
epic:         draft → planned → done (child stories linkage)
sprint:       planned → in_progress → done
sprint planning:   planned → in_progress (select items, assign, capacity check, commitment)
sprint review:    in_progress → done (completed/incomplete stories, notes, client feedback)
sprint retrospective: planned → in_progress → done (what went well, what went wrong, improvements)
```

## 5. Security design (proposed)

- New groups: `group_amnus_agile_user`, `group_amnus_agile_manager`, `group_amnus_agile_admin` implying the
  existing AMNUS project groups (user → manager → admin), plus `amnus_core.group_amnus_user` via project user.
- ACLs for `amnus.agile.*` models; record rules: company isolation + project visibility mirroring AMNUS project
  rules; manager all-rule.
- No auto-assignment of new groups to existing users; no weakening of standard project security.
- Sprint closure/modification restricted to manager group.

## 6. Integration design

- `amnus_agile` depends on: `amnus_core`, `amnus_projects`, `project`, `mail` (minimum); integration points:
  - handover → sprint/backlog via `project.project.amnus_request_id` traceability.
  - deliverable accepted → story/task completion signal.
  - CRM request approved → epic/backlog seeding (future).

## 7. UI architecture (proposed)

- Backlog: list/form with epics, stories, filters by project/priority/state.
- Sprint: kanban over sprint state; sprint planning view (backlog selection, assignment, capacity).
- User story form: description, acceptance criteria, business value, points, epic, linked task.
- Epic views; sprint dashboard; burndown; velocity — native Odoo views, OWL only if needed; no Enterprise components.

## 8. Testing strategy (proposed)

- Installation, backlog CRUD, epic-story relations, sprint CRUD, planning assignment/capacity, state transitions,
  security (manager-only closure), cross-company isolation, regression on `amnus_core`, `amnus_crm`, `amnus_projects`.

## 9. Risks and open decisions

- Story vs. task model boundary; points scale; capacity model; burndown source; team/capacity data availability.
- Risk: over-abstraction; mitigate by reusing `project.task` and `amnus.project.deliverable`.

## 10. Implementation sequence (proposed)

1. Freeze design (this document + product decisions).
2. `amnus_agile` models + security.
3. Views / kanban / planning.
4. Reports (velocity/burndown).
5. Tests + regression.
6. Delivery.

## 11. Recommendation

**READY FOR IMPLEMENTATION** pending product decisions on story points scale, burndown source and story-vs-task ownership.
No implementation was performed during this discovery sprint.

## Appendix A — Verified sources consulted

- `C:\Program Files\AmanusERP\odoo\addons\project\models\project_task.py`
- `C:\Program Files\AmanusERP\odoo\addons\mail\models\mail_activity_mixin.py`
- `C:\Program Files\AmanusERP\odoo\addons\project/models/project_project.py`
- Sprint 03 artifacts: `addons/amnus/amnus_projects/**`, `docs/technical/amnus_projects.md`, `docs/sprints/SPRINT_03*.md`

## Appendix B — Environment

- Branch: `main` @ `dc2934d` (post Sprint 03 merge).
- Database: `amnus_test_19` (read-only usage; no changes made during discovery).
