# AMNUS Agile

Agile and Scrum planning for the AMNUS Odoo Project Lifecycle Management Platform.

`amnus_agile` adds a planning layer on top of standard Odoo 19 Project. It does
**not** replace or duplicate `project.task`: tasks remain the single execution
model (stages, assignees, deadlines, activities). User stories are planning
artifacts that may link to one task.

## Reused standard models

| Standard model | Usage |
|----------------|-------|
| `project.project` | planning container for stories, epics and sprints |
| `project.task` | execution model; optional one-to-one link from a story |
| `project.task.type` | task stages (untouched) |
| `res.company` | multi-company isolation |
| `mail` | chatter/activities infrastructure (no duplicate messaging model) |
| `amnus.tag` | story classification (`amnus_core`) |
| `amnus.audit.log` | audit trail (`amnus_core`) |

No duplicate task, stage, state or assignment model is created.

## Models

### `amnus.agile.user.story` (new)

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | story title, required |
| `description` | Text | detailed description |
| `acceptance_criteria` | Text | required before completion |
| `business_value` | Text | optional business justification |
| `tag_ids` | Many2many `amnus.tag` | `check_company=True` |
| `project_id` | Many2one `project.project` | required, cascade; immutable once linked |
| `epic_id` | Many2one `amnus.agile.epic` | must belong to the same project |
| `sprint_id` | Many2one `amnus.agile.sprint` | one sprint at a time; must match project/company |
| `task_id` | Many2one `project.task` | at most one story per task (`unique (task_id)`) |
| `task_state` | Selection (related) | read-only execution status |
| `task_user_ids` | Many2many (related) | read-only task assignees |
| `sequence` | Integer | backlog order (drag handle) |
| `priority` | Selection | low / medium / high / urgent |
| `story_points` | Integer | Fibonacci: 1, 2, 3, 5, 8, 13, 21 |
| `state` | Selection | backlog / planned / in_progress / done / cancelled |
| `company_id` | Many2one (related, stored) | from `project_id` |
| `active` | Boolean | archive instead of deleting |

### `amnus.agile.epic` (new)

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | required |
| `project_id` | Many2one `project.project` | required; immutable once it has stories |
| `description` | Text | scope |
| `company_id` | Many2one (related, stored) | from `project_id` |
| `sequence` | Integer | ordering |
| `state` | Selection | open / done |
| `story_count` | Integer (computed) | number of linked stories |
| `completed_story_count` | Integer (computed) | stories in `done` |
| `progress` | Float (computed) | percentage of completed stories |
| `active` | Boolean | archive support |

### `amnus.agile.sprint` (new)

| Field group | Fields | Notes |
|-------------|--------|-------|
| Identity | `name`, `project_id`, `company_id`, `goal`, `active` | project required |
| Dates | `date_start`, `date_end` | end cannot precede start |
| Lifecycle | `state` | draft / planned / active / closed / cancelled |
| Backlog | `story_ids` | one2many stories |
| Capacity | `capacity_points` | manual Story Point capacity |
| Live metrics | `committed_points`, `completed_points`, `carry_over_points` | computed |
| Baseline | `baseline_points` | captured at activation |
| Frozen metrics | `final_committed_points`, `final_completed_points`, `final_carry_over_points` | captured at closure/cancellation |
| Velocity | `velocity_points` | frozen completed points when closed |
| History | `membership_ids` | read-only membership rows |
| Burndown | `burndown_point_ids` | read-only dated points |
| Review | `review_summary`, `review_accepted_outcomes`, `review_incomplete_work` | structured review |
| Retrospective | `retrospective_observations`, `retro_went_well`, `retro_did_not_go_well` | structured retrospective |
| Improvement | `improvement_actions`, `action_owner_id`, `action_target_date` | follow-up ownership |

### `amnus.agile.sprint.membership` (new)

Append-only history of a story's participation in a sprint.

| Field | Type | Notes |
|-------|------|-------|
| `sprint_id`, `story_id` | Many2one | `unique (sprint_id, story_id)` |
| `project_id`, `company_id` | Many2one (related, stored) | isolation |
| `date_added`, `added_by_id` | Datetime / Many2one | set by the server |
| `date_removed`, `removed_by_id` | Datetime / Many2one | set when the membership ends |
| `committed_points` | Integer | Story Points at commitment |
| `final_points` | Integer | Story Points when the membership ended |
| `outcome` | Selection | active / completed / incomplete / carried_over / removed / cancelled |
| `carry_over_sprint_id` | Many2one | destination sprint |
| `reason` | Text | carry-over or removal reason |

### `amnus.agile.burndown` (new)

| Field | Type | Notes |
|-------|------|-------|
| `sprint_id` | Many2one | required, cascade |
| `date` | Date | event date |
| `remaining_points` | Integer | remaining Story Points |
| `completed_points` | Integer | completed Story Points |

### `amnus.agile.carry.over.wizard` (new, transient)

Helper form to select unfinished stories, a destination sprint and a reason;
calls `action_carry_over()` on the source sprint.

## Story workflow

```
backlog --Plan--> planned --Start--> in_progress --Done--> done
   |                 |                   |
   +----Cancel-------+-----Cancel--------+--> cancelled
```

Server-enforced rules:

- Only documented transitions are accepted; backward moves are rejected.
- `action_done()` requires `in_progress`, non-empty acceptance criteria and an
  AMNUS Agile Manager.
- Task state never completes a story; deliverable acceptance is a separate
  contractual concept.
- Story Point estimation and planning-state changes are manager-only (enforced in
  `write()`, not only in the UI).
- Only one story per task and one sprint per story.
- Cross-project and cross-company links are rejected.

## Sprint workflow

```
draft --> planned --> active --> closed
  |          |          |
  +----------+----------+--> cancelled
```

- `action_plan()`: draft → planned.
- `action_start()`: planned → active; records `baseline_points`, refreshes
  membership commitment snapshots and writes the baseline burndown point.
- `action_close()`: active → closed; records the closing burndown point, freezes
  `final_*` metrics and closes open memberships (`completed`, `incomplete` or
  `cancelled`).
- `action_cancel()`: freezes the same figures and closes memberships as
  `cancelled`.
- `action_carry_over()`: moves unfinished stories to another sprint of the same
  project/company; the source membership becomes `carried_over` with destination
  and reason, and a new membership row opens in the target sprint.
- Closed sprints cannot be reopened.

## Metrics

```
live committed   = Σ story_points where state != cancelled
live completed   = Σ story_points where state == done
live carry-over  = live committed − live completed
velocity (sprint)    = frozen completed points if state == closed, else 0
velocity (selection) = mean(velocity(sprint)) over closed sprints
```

Frozen closure figures mean later Story Point edits cannot rewrite historical
velocity or burndown.

## Security

New groups (never auto-assigned):

| Group | Implies |
|-------|---------|
| `group_amnus_agile_user` | `amnus_core.group_amnus_user`, `amnus_projects.group_amnus_project_user` |
| `group_amnus_agile_manager` | agile user, `amnus_projects.group_amnus_project_manager` |
| `group_amnus_agile_admin` | agile manager |

- Agile users: read-only on stories, epics, sprints, membership and burndown.
- Agile managers: CRUD on stories, epics, sprints and the transient wizard;
  read-only on membership and burndown.
- Membership history and burndown are written only by server workflows in
  `sudo`; direct client create/write/unlink is denied.
- Multi-company record rules on every model plus project-visibility rules.
- No standard Odoo or AMNUS group, ACL or record rule is weakened.

## Views and menus

Under *AMNUS → Agile*: Product Backlog (list, kanban, form, search), Epics
(list, kanban, form, search), Sprints (list, kanban, form with Backlog, Review,
Retrospective, Burndown and Membership History tabs), and
*Reporting → Burndown / Velocity*.

All views use Odoo 19 `<list>` syntax. No OWL component and no Enterprise feature
is used.

## Dependencies

- `amnus_core` — tags, audit log, security groups, AMNUS root menu
- `amnus_projects` — AMNUS project model and project lifecycle
- `project` — standard project/task models
- `mail` — chatter/activity infrastructure

## Installation

Install `amnus_core`, `amnus_projects` and `project`, then install `amnus_agile`.
Assign the AMNUS Agile groups explicitly to the relevant users.

## Tests

```
odoo-bin -c <config> -d <test_db> -u amnus_agile \
  --test-enable --test-tags amnus_agile --stop-after-init
```

60 tests, 0 failures, 0 errors (installation, user story, epic, sprint,
burndown/velocity, security).

## Internationalization

User-facing strings are wrapped in `_()`. `i18n/amnus_agile.pot` contains 192
messages; `fr_FR` and `ar_SA` are fully translated (192/192 each).

Odoo 19 Community Edition only. No Enterprise dependencies.
No modifications to existing `amanus_*` modules or Odoo core.

## Known limitations

- Burndown is event-based; event-free days have no row.
- Sprint capacity is manual; there is no team/availability model in this release.
- Re-estimating points inside an active sprint changes live figures (historical
  snapshots remain frozen).
- Arabic translations were reviewed for meaning only; visual RTL review was not
  performed.
