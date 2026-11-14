# AMNUS Projects

Project lifecycle extension for the AMNUS Odoo Project Lifecycle Management Platform.

`amnus_projects` extends standard Odoo 19 Project (`project.project`, `project.task`)
instead of replacing it. It adds the AMNUS handover from an approved CRM
implementation request, a contractual deliverable model with a controlled
acceptance workflow, and AMNUS metadata (tags, request origin, actual go-live).

## Reused standard models

| Standard model | Usage |
|----------------|-------|
| `project.project` | extended with AMNUS fields and lifecycle metadata |
| `project.project.stage` | project lifecycle (no AMNUS stage model) |
| `project.task` | extended with an optional deliverable link |
| `project.task.type` | task stages (untouched) |
| `project.task.state` | task states (untouched) |
| `last_update_status` | project health (untouched) |
| `mail.thread` | chatter on projects and deliverables |

No duplicate project, task, stage, state or health model is created.

## Models

### `project.project` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `amnus_is_amnus_project` | Boolean | flags projects managed through AMNUS; indexed, not copied |
| `amnus_request_id` | Many2one `amnus.crm.project.request` | authoritative origin link; unique at database level, read-only in the UI |
| `amnus_request_type` | Selection (related, stored) | mirrors the request type for filtering/grouping |
| `amnus_actual_go_live` | Date | actual go-live, distinct from the planned end (`date`) |
| `amnus_deliverable_ids` | One2many `amnus.project.deliverable` | project deliverables |
| `amnus_deliverable_count` | Integer (computed) | smart-button counter |
| `amnus_tag_ids` | Many2many `amnus.tag` | platform classification, carried from the opportunity |

Planned dates reuse standard fields:

- planned start → `date_start`
- planned go-live / project end → `date` (labelled *Expiration Date* by Odoo)
- actual go-live → `amnus_actual_go_live`

Lifecycle and health reuse standard `stage_id` and `last_update_status`.

### `project.task` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `amnus_deliverable_id` | Many2one `amnus.project.deliverable` | optional; the deliverable must belong to the task's project |

Task states, stages, assignees, deadlines, milestones and visibility are standard
Odoo behavior.

### `amnus.project.deliverable` (new)

A deliverable is a contractual output, not a milestone: it carries a type, an
acceptance workflow, a sign-off identity/timestamp and a rejection reason.

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char | required, tracked |
| `project_id` | Many2one `project.project` | required, cascade on project deletion, immutable after submission |
| `sequence` | Integer | ordering, default 10 |
| `type` | Selection | document / software / migration / integration / training / other |
| `description` | Text | scope and acceptance criteria |
| `responsible_id` | Many2one `res.users` | defaults to the current user |
| `due_date` | Date | contractual due date |
| `state` | Selection | draft / submitted / accepted / rejected |
| `submitted_by` / `submitted_date` | Many2one / Datetime | set by the submit action |
| `accepted_by` / `accepted_date` | Many2one / Datetime | set by the accept action |
| `rejected_by` / `rejected_date` | Many2one / Datetime | set by the reject action |
| `rejection_reason` | Text | mandatory to reject |
| `company_id` | Many2one `res.company` | related `project_id.company_id`, stored, read-only |
| `tag_ids` | Many2many `amnus.tag` | platform classification |
| `task_ids` / `task_count` | One2many / Integer | contributing tasks and counter |
| `active` | Boolean | archive instead of deleting accepted deliverables |

### `amnus.crm.project.request` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | Many2one `project.project` | created project; read-only, written only by the handover action |
| `project_count` | Integer (computed) | 0 or 1 |

## Deliverable workflow

```
draft ──Submit──▶ submitted ──Accept──▶ accepted
  ▲                   │
  │                   └──Reject──▶ rejected
  └────────Reset to Draft───────────┘
```

Rules enforced server-side (not only in the view):

- A deliverable is always created in `draft`; sign-off fields cannot be set on create.
- `state` and all sign-off fields cannot be written through RPC. The workflow
  methods use `sudo()` **after** their own authorization checks, so a direct
  `write({'state': 'accepted'})` is always rejected.
- Submission: the responsible user or an AMNUS Project Manager.
- Accept / Reject / Reset to draft: AMNUS Project Manager only.
- Rejection requires a non-empty reason.
- Accepted deliverables are immutable for non-managers and cannot be deleted;
  the project cannot be deleted while it contains accepted deliverables (archive it).
- Identity and timestamps are derived from `self.env.user`, never from arguments.
- Every transition writes an `amnus.audit.log` event.

## CRM → Projects handover

`action_create_project()` on an approved `amnus.crm.project.request`:

1. Checks the caller belongs to `group_amnus_project_manager` (or superuser).
2. Checks request/opportunity/customer/project company consistency. Child contacts
   without their own company are resolved through their commercial entity.
3. Locks the request row with `SELECT ... FOR UPDATE`, then re-checks that the
   request is still `approved` and not yet linked.
4. Creates one `project.project` with the mapped values and sets
   `amnus_is_amnus_project = True`.
5. Writes the request backlink (`project_id`), logs an audit event and posts a
   message on the project chatter.
6. Returns an action opening the new project.

The `UNIQUE (amnus_request_id)` SQL constraint is the final safety net against
concurrent or repeated handovers. The request is never updated manually (no
manual `commit`); the transaction guarantees all-or-nothing behavior.

## Security

New groups (never auto-assigned):

| Group | Implies | Access |
|-------|---------|--------|
| `group_amnus_project_user` | `amnus_core.group_amnus_user`, `project.group_project_user`, `project.group_project_stages` | read standard projects; CRUD deliverables (no delete) |
| `group_amnus_project_manager` | project user, `project.group_project_manager` | full project management, handover, deliverable sign-off |
| `group_amnus_project_admin` | project manager | full AMNUS project administration |

- No standard Odoo group, ACL or record rule is weakened or modified.
- `amnus_core` groups (`noupdate="1"`) are referenced only, never altered.
- Deliverable record rules: multi-company isolation + project visibility mirroring
  standard project visibility + manager all-rule.
- Direct RPC writes to `request.project_id` and `project.amnus_request_id` are blocked.

## Views and menus

Under the AMNUS root menu:

- **Projects → Projects** — standard project list/form with an *AMNUS Projects* filter,
  deliverable smart button, request smart button and an *AMNUS Implementation* group.
- **Projects → Deliverables** — list / form / search with workflow buttons, status
  filters and group-bys.
- **Projects → Configuration → Project Stages** — standard stage configuration.
- CRM request form: *Create Project* (approved, not linked, manager only) and
  *View Project* buttons, plus an *Approved, Not Handed Over* search filter.
- Task form: optional *Deliverable* field; task search: *AMNUS Deliverable Tasks* filter.

## Recommended stage mapping

The addon ships **no stage data**; the standard stage model is reused. A suggested
mapping for AMNUS implementation projects:

| Standard project stage | AMNUS meaning |
|------------------------|---------------|
| New | Handed over, not started |
| In Progress | Discovery / build |
| Done | Delivered, pending acceptance |
| Cancelled | Cancelled |

Adjust names in *Projects → Configuration → Project Stages* to match your process.

## Dependencies

- `amnus_core` — tags, audit log, security groups, AMNUS root menu
- `amnus_crm` — implementation request model
- `project` — standard project/task/stage/state models
- `mail` — chatter on projects and deliverables

`sale` is intentionally not a dependency.

## Installation

Install `amnus_core`, `amnus_crm` and `project`, then install `amnus_projects`.
Assign the AMNUS project groups explicitly to the relevant users.

## Tests

Run with:

```
odoo-bin -c <config> -d <test_db> -u amnus_projects --test-enable --test-tags amnus_projects --stop-after-init
```

61 tests, 0 failures, 0 errors (installation, project integration, CRM handover,
deliverables, task integration, security).

## Internationalization

User-facing strings are wrapped in `_()`. `fr_FR` and `ar_SA` translations are
provided under `i18n/`.

Odoo 19 Community Edition only. No Enterprise dependencies.
No modifications to existing `amanus_*` modules.
