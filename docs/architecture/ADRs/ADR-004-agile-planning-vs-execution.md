# ADR-004 — Agile Planning Artifacts vs. Task Execution

## Status

Accepted — Sprint 04

## Context

AMNUS needs Agile/Scrum planning on top of Odoo implementation projects:
product backlog, epics, user stories, sprint planning, capacity, commitment,
completion, review, retrospective, carry-over, velocity and burndown.

Odoo already provides `project.task` with stages, states, assignees, deadlines,
activities and reporting. Two risks drive this decision:

1. **Duplicated execution model.** Creating Agile task/stage/state models would
   split execution data, duplicate UI and break standard Project reporting.
2. **Unverifiable history.** If "completed points", "velocity" and "sprint
   membership" are recomputed from live data only, re-estimating a story later
   silently rewrites past performance, and carry-over leaves no trace.

A third risk is conceptual: mixing Agile story completion with contractual
deliverable acceptance (`amnus.project.deliverable`).

## Decision

### 1. Stories are planning artifacts; tasks own execution

- `amnus.agile.user.story` owns planning metadata only: title, description,
  business value, acceptance criteria, priority, sequence, Story Points, epic,
  sprint, optional task link and tags.
- `project.task` remains the single execution model (assignee, stage, state,
  deadline, activities, chatter).
- A story may link to **at most one** task (`unique (task_id)`); a task may be
  linked to at most one story.
- `task_state` and `task_user_ids` are read-only related fields for visibility,
  never writable planning data.
- Story completion never depends on task state, and task closure never depends
  on story state.

### 2. Explicit story completion

- `action_done()` requires: story `in_progress`, non-empty acceptance criteria,
  and an AMNUS Agile Manager (or superuser).
- Only documented transitions are accepted; backward transitions are rejected.
- Carry-over is the only path from `in_progress` back to `planned`, and it is
  gated by an internal context flag plus manager authorization.

### 3. Deliverable acceptance is a separate contract

`amnus.project.deliverable.state == 'accepted'` is contractual sign-off. It does
not complete stories, and story completion does not accept deliverables.

### 4. Append-only sprint membership history

- New model `amnus.agile.sprint.membership`, unique per `(sprint, story)`.
- Direct client create/write/unlink is denied for every group; rows are written
  only by server workflows in `sudo`.
- Each row records the commitment snapshot, the final Story Points, the outcome
  (`completed`, `incomplete`, `carried_over`, `removed`, `cancelled`), the
  carry-over destination and the reason.

### 5. Frozen closure metrics

- Sprint activation captures `baseline_points` and refreshes the membership
  commitment snapshots.
- Sprint closure/cancellation writes `final_committed_points`,
  `final_completed_points` and `final_carry_over_points`.
- Computed metrics return the frozen values for closed/cancelled sprints.
- Closed sprints cannot be reopened.
- Velocity is computed from frozen completed points only.

### 6. Event-based burndown

- Burndown rows are created from dated sprint/story events (start, closure,
  story state changes inside an active sprint).
- No synthetic daily rows are generated.
- Remaining and completed points are stored, never recomputed from current data.

### 7. Dedicated Agile security groups

- `group_amnus_agile_user` implies `amnus_core.group_amnus_user` and
  `amnus_projects.group_amnus_project_user`.
- `group_amnus_agile_manager` implies the agile user group and the AMNUS project
  manager group.
- `group_amnus_agile_admin` implies the agile manager group.
- No standard Odoo or AMNUS group, ACL or record rule is modified or weakened.
- Groups are never auto-assigned.

### 8. Odoo 19 constraint API

`models.Constraint` is used for database-level uniqueness. The legacy
`_sql_constraints` attribute is no longer supported by Odoo 19 and is not used.

## Consequences

- Standard Project remains fully usable without Agile; stories are additive.
- Historical velocity and burndown cannot be rewritten by later edits.
- Carry-over is auditable end to end.
- Two sources of truth exist by design: planning (stories) and execution
  (tasks). This is intentional and documented, not accidental duplication.
- Agile users cannot create, edit or delete membership or burndown rows, so
  metrics cannot be forged through RPC.
- Manual sprint capacity is a known limitation until a team/availability model
  is introduced in a later sprint.

## Alternatives rejected

- **Agile task model duplicating `project.task`** — splits execution and
  reporting, violates reuse rules.
- **Storing sprint membership only on `story.sprint_id`** — loses carry-over
  history and commitment snapshots.
- **Recomputing velocity from live stories** — rewrites past performance after
  re-estimation.
- **Reusing deliverable acceptance as story completion** — conflates contractual
  sign-off with Agile flow.
