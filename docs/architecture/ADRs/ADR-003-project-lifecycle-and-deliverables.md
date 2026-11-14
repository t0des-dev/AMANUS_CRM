# ADR-003 — Project Lifecycle Reuse and Deliverable Sign-off

## Status

Accepted — Sprint 03

## Context

AMNUS needs to manage Odoo implementation projects after an approved CRM
request. Two risks drive this decision:

1. Odoo already provides projects, project stages, task stages, task states,
   project health and milestones. Creating parallel AMNUS models would split
   reporting, duplicate UI and break standard features.
2. Deliverable acceptance is a contractual sign-off. If it is only enforced in
   the view or through client-controllable context flags, any RPC caller can
   forge acceptance, identity or timestamps.

## Decision

### 1. Extend standard Project; do not replace it

- `project.project` is inherited for AMNUS metadata only.
- Project lifecycle = `project.project.stage` (no AMNUS stage model).
- Task lifecycle = `project.task.type` / task `state` (untouched).
- Project health = `last_update_status` (untouched).
- Planned dates = standard `date_start` and `date`; actual go-live is the single
  additive date `amnus_actual_go_live`.
- The only new business model is `amnus.project.deliverable`.

### 2. One authoritative request link

- `project.project.amnus_request_id` is the authoritative link, protected by
  `UNIQUE (amnus_request_id)`.
- `amnus.crm.project.request.project_id` is a convenience backlink, validated by
  a constraint and writable only by the handover (superuser context).
- The handover locks the request row (`SELECT ... FOR UPDATE`), re-checks state
  and existing link, then creates the project. No manual commit.

### 3. Server-authoritative deliverable workflow

- `action_submit`, `action_accept`, `action_reject`, `action_reset_to_draft`
  perform explicit authorization, then write through `self.sudo().write()`.
- `create` and `write` reject direct `state` and sign-off field writes outside a
  superuser context. `self.env.su` is the boundary; context flags and RPC
  arguments are never trusted.
- Identities and timestamps are derived from `self.env.user` and
  `fields.Datetime.now()`.
- Rejection requires a non-empty reason.
- Accepted deliverables are frozen for non-managers and cannot be deleted; a
  project containing accepted deliverables cannot be deleted either (archive it).
- Every transition writes an `amnus.audit.log` event.

### 4. Dedicated project security groups

- New groups imply the standard Odoo project groups instead of duplicating
  project access.
- No standard Odoo group, ACL or record rule is modified or weakened.
- Groups are never auto-assigned at install; assignment is an explicit
  administrative decision.
- Deliverable record rules reuse company isolation and standard project
  visibility.

## Consequences

- Standard Odoo project reporting, stages and task features keep working.
- AMNUS adds only one table with business meaning (`amnus.project.deliverable`)
  plus relation tables.
- Sign-off cannot be forged through direct ORM/RPC writes.
- Accepted deliverables are intentionally hard to destroy; corrections require
  an explicit manager decision on a new revision, not silent mutation.
- Stage naming remains an operational configuration task; the addon ships no
  stage data to avoid imposing a process.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| New `amnus.project` model | duplicates project/task/stage/health; breaks standard UI and reporting |
| New AMNUS stage/state models | same duplication problem; Odoo stages already cover lifecycle |
| Milestones as deliverables | milestones have no type, acceptance workflow, sign-off or rejection reason |
| View-level workflow guards | trivially bypassed through RPC |
| Context-flag-based write guards | context keys are client-controllable through RPC |
| Auto-assigning project groups | silently widens the access of the existing user base |

## Related

- ADR-001 (Core Module)
- ADR-002 (Security Model)
- `docs/technical/amnus_projects.md`
- `docs/sprints/SPRINT_03_DISCOVERY.md`
