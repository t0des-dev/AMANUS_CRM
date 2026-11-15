# AMNUS Agile — Technical Design

Addon: `addons/amnus/amnus_agile`
Version: `19.0.1.0.0`
Depends: `amnus_core`, `amnus_projects`, `project`, `mail`

## 1. Scope

`amnus_agile` adds an Agile/Scrum planning layer to the AMNUS implementation
lifecycle. It provides a product backlog, epics, user stories, sprints, sprint
membership history, review/retrospective records and historical metrics.

It does **not** replace or duplicate Odoo Project. `project.task` remains the
single execution model (assignees, stages, deadlines, activities, execution
workflow). `amnus.project.deliverable` remains the contractual acceptance model.

## 2. Model ownership

| Model | Responsibility |
|-------|----------------|
| `amnus.agile.user.story` | Planning artifact: title, description, business value, acceptance criteria, priority, sequence, Story Points, epic, sprint, optional task link, tags |
| `amnus.agile.epic` | Project-level grouping of user stories with derived progress |
| `amnus.agile.sprint` | Time-boxed iteration: lifecycle, capacity, commitment, live and frozen metrics, review and retrospective |
| `amnus.agile.sprint.membership` | Append-only history of a story's membership in a sprint, Story Points at commitment, outcome and carry-over destination |
| `amnus.agile.burndown` | Dated historical metric points of a sprint |
| `amnus.agile.carry.over.wizard` | Transient helper for the explicit carry-over action |

### Story vs. task boundary

- The story owns **planning metadata**: Story Points, epic, sprint, priority,
  acceptance criteria, business value.
- `project.task` owns **execution data**: assignee (`user_ids`), stage
  (`stage_id`), state (`state`), deadline, activities.
- The story exposes `task_state` and `task_user_ids` as read-only,
  access-safe computed fields for visibility. They are never copied into writable
  story fields and never computed with sudo escalation; inaccessible task data is
  omitted rather than disclosed.
- A task may be linked to **at most one** story (ORM/DB constraint).
- Deleting a task clears the link (`ondelete='set null'`); the story is kept.
- Both models must belong to the same project and company.
- A task linked to an Agile story cannot be moved to another project/company
  while the link exists (enforced on `project.task.write` and story validation).

### Story completion rule

A story becomes `done` only through `action_done()`, which requires:

1. the story is `in_progress`;
2. `acceptance_criteria` is non-empty;
3. the caller is an AMNUS Agile Manager (or superuser).

The task state **never** completes the story automatically: a task in a generic
closed stage is not evidence that acceptance criteria were met. Conversely, a
done story does not automatically close its task. This keeps Agile completion
and execution workflow separate.

Contractual deliverable acceptance (`amnus.project.deliverable.state ==
'accepted'`) is a **different** concept and does not drive story completion.

### Story lifecycle

```
backlog ──Plan──> planned ──Start──> in_progress ──Done──> done
   │                 │                   │
   └────Cancel───────┴─────Cancel────────┴────> cancelled
```

Only documented transitions are accepted. Backward moves and completion of a
`done`/`cancelled` story are rejected. Carry-over is the only path that turns an
`in_progress` story back into `planned`, and it is gated by an internal context
flag plus manager authorization.

## 3. Epic

- An epic belongs to one project and one company.
- `story_count`, `completed_story_count` and `progress` are computed from the
  linked stories' states (not from task counts).
- The project of an epic that already has stories cannot be changed.
- `action_done()` is manager-only and only valid from `open`.

## 4. Sprint lifecycle

```
draft ──> planned ──> active ──> closed
  │          │          │
  └──────────┴──────────┴──> cancelled
```

- Dates: `date_end >= date_start`.
- Direct ORM/RPC `state` writes are rejected; transitions are performed only by
  authorized workflow actions through internal server-side writes.
- `baseline_points` and `final_*` snapshot fields are protected from direct
  create/write; they are captured only by workflow transitions.
- Every story in a sprint must belong to the same project and company.
- A story can only be in one sprint at a time (`sprint_id`).
- Only AMNUS Agile Managers may plan, start, close or cancel a sprint.
- A closed sprint cannot be reopened; `closed` and `cancelled` are terminal.
- Closed/cancelled sprints and their historical records cannot be deleted.
- Closing a sprint never marks unfinished stories as done.
- The project of a sprint that contains stories cannot be changed.

### Commitment baseline

On `action_start()`:

- `baseline_points` = current live committed points;
- every open membership row refreshes `committed_points` from the story points
  at that moment (the commitment baseline);
- a burndown point is recorded on `date_start` with `remaining = baseline`.

### Closure freeze

On `action_close()`:

- the burndown point for `date_end` is recorded from live figures;
- `final_committed_points`, `final_completed_points` and
  `final_carry_over_points` are written;
- the sprint becomes `closed`, so the computed `committed_points` /
  `completed_points` / `carry_over_points` fields return the frozen values;
- open membership rows are closed with `completed`, `incomplete` or `cancelled`;
- the audit log records the transition.

`action_cancel()` freezes the same figures and closes memberships with
`cancelled`.

## 5. Sprint membership and carry-over

`amnus.agile.sprint.membership` is append-only history. Direct client
create/write/unlink access is denied by ACLs and defended in ORM; only controlled
server-side workflows (executed in `sudo` after authorization/validation) create
or close rows. Closed membership rows are immutable and cannot be deleted.

Each row records: sprint, story, project, company, added date/user, removed
date/user, original committed points, final points, outcome, carry-over
destination and reason.

- Adding a story to an open sprint opens/refreshes an open membership row.
- Removing a story or moving it to another open sprint closes the current open
  row with the appropriate outcome.
- Carry-over is allowed only from an open (non-closed/cancelled) source sprint.
  It closes the source open membership as `carried_over` (without rewriting
  closed history), stores destination/reason, and opens a membership in the
  target sprint.
- Re-entry into the same sprint after a historical membership exists is rejected
  to preserve append-only history.
- One row per `(sprint, story)` pair; one open membership per story at a time.

## 6. Capacity, velocity and burndown

### Story Points

Allowed values: `1, 2, 3, 5, 8, 13, 21`; empty is allowed until estimated.
Only Agile Managers may estimate or re-estimate.

### Capacity

`capacity_points` is manually entered on the sprint (Story Points). No
availability, holiday, timesheet or working-hour calculation is performed in
this release.

### Velocity

- Per sprint: `velocity_points` = completed Story Points when the sprint is
  `closed`, otherwise `0`.
- Project/portfolio velocity: `_get_sprint_velocity(sprint_ids=None)` returns
  the arithmetic mean of `velocity_points` over the selected closed sprints.
- Velocity uses the frozen `final_completed_points` captured at closure, so later
  Story Point edits cannot rewrite past velocity.

### Burndown

- Data source: `amnus.agile.burndown` dated events created by controlled
  server-side workflows (append-only, immutable). Events include baseline,
  scope add/remove, re-estimation, work start, completion, carry-over in/out,
  cancellation and closure.
- Each event stores sprint/date/type/story, remaining and completed points, and
  points before/after where applicable, with deterministic ordering
  (`date`, `event_sequence`, `id`).
- Nothing is fabricated for periods before tracking; event-free days do not
  imply zero remaining work. `get_burndown_series()` returns a continuous daily
  series carrying the last known values forward.
- Baseline commitment is exposed as `baseline_points`; closure metrics are frozen
  in `final_*` fields.
- Historical events are not rewritten by later story point edits or later sprint
  changes.

## 7. Security

Groups (never auto-assigned):

- `amnus_agile.group_amnus_agile_user` implies `amnus_core.group_amnus_user`
  and `amnus_projects.group_amnus_project_user`.
- `amnus_agile.group_amnus_agile_manager` implies the agile user group and
  `amnus_projects.group_amnus_project_manager`.
- `amnus_agile.group_amnus_agile_admin` implies the agile manager group.

ACLs:

- Agile users: read-only on stories, epics, sprints, memberships and burndown.
- Agile managers: CRUD on stories, epics and sprints; read-only on membership
  history and burndown (written only by server workflows); CRUD on the
  transient carry-over wizard.
- Agile administrators: same model permissions as managers; group administration
  remains governed by `base.group_system`.

Record rules:

- Multi-company rule on every model (`company_id in company_ids + [False]`).
- Project visibility rule for agile users, mirroring AMNUS project visibility
  (`project_id.privacy_visibility` plus follower/project-manager membership).
- Managers see all records of their allowed companies.

Server-side protections (not UI-only):

- Direct ORM/RPC lifecycle state changes and frozen snapshot writes are rejected;
  workflow actions use internal server-side writes after authorization.
- Manager checks in every workflow action and in create/write guards for protected
  planning operations, including sprint membership and Story Point changes.
- Closed/cancelled sprints cannot be reopened or deleted; closed metrics and
  history remain immutable.
- Membership and burndown are not client-writable/deletable and are defended in ORM.
- Stories cannot be assigned to closed/cancelled sprints; carry-over from closed
  sources is rejected and cannot rewrite closed source history.
- Cross-project and cross-company story/task links are rejected; linked tasks
  cannot be moved across project/company; task-derived fields do not expose
  inaccessible data via sudo.
- Audit events are written through `amnus.audit.log._log_event`.

## 8. Views and reporting

- Product Backlog: list (with drag handle), kanban, form and search.
- Epics: list, kanban, form and search.
- Sprints: list, kanban, form (backlog, review, retrospective, burndown and
  membership history tabs), search, carry-over wizard.
- Reporting: burndown line graph/list and closed-sprint velocity bar graph/list
  under *AMNUS → Agile → Reporting*.

All views use Odoo 19 `<list>` syntax. No OWL component and no Enterprise
feature (Gantt, Spreadsheet, dashboards) is used.

## 9. Historical accuracy limitations

- Burndown is event-based, not a daily snapshot: days without a sprint/story
  event have no row.
- Re-estimating a Story Point value inside an **active** sprint changes the
  live remaining/completed figures; the stored `committed_points` snapshot of
  each membership and the frozen closure figures preserve the audit trail.
- The sprint activation baseline is a single scalar; per-membership original
  points are stored on membership rows.
- Sprint capacity is manual; no team availability model exists in Community
  Edition.
- Arabic translations were reviewed for meaning only; visual RTL review was not
  performed in this sprint.

## 10. Metrics formulas

```
live committed  = Σ story_points where state != cancelled
live completed  = Σ story_points where state == done
live carry-over = live committed − live completed
membership committed points = story points at commitment (sprint start refresh)
membership final points     = story points when the membership ended
velocity (sprint)           = frozen completed points, if state == closed else 0
velocity (selection)        = mean(velocity (sprint)) over closed sprints
```
