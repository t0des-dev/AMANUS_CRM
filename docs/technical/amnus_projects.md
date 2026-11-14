# AMNUS Projects — Technical Documentation

## Overview

`amnus_projects` implements the AMNUS project lifecycle on top of standard Odoo 19
Project. It:

- converts an approved `amnus.crm.project.request` into a real `project.project`;
- adds AMNUS lifecycle metadata to `project.project`;
- adds the business model `amnus.project.deliverable` with a controlled
  acceptance workflow;
- links `project.task` records to deliverables with project consistency checks;
- reuses `amnus_core` tags, audit log and security groups.

Standard project stages (`project.project.stage`), task stages
(`project.task.type`), task states and project health (`last_update_status`) are
reused as-is. The addon ships no stage data and no duplicate lifecycle models.

## Module manifest

- Name: AMNUS Projects
- Version: 19.0.1.0.0
- Category: Services/Project
- License: LGPL-3
- Depends: `amnus_core`, `amnus_crm`, `project`, `mail`
- Application: True
- Installable: True
- Auto install: False

`sale` is intentionally not a dependency. `mail` is declared explicitly for the
chatter used on deliverables and on projects.

## Reused standard models

- `project.project` — extended (not replaced)
- `project.project.stage` — project lifecycle
- `project.task` — extended with one optional field
- `project.task.type` — task stages
- `project.task.state` — task states
- `project.project.last_update_status` — project health
- `mail.thread` — chatter

## Custom model: `amnus.project.deliverable`

### Fields

| Field | Type | Attributes |
|-------|------|------------|
| `name` | Char | required, tracking |
| `project_id` | Many2one (`project.project`) | required, ondelete=cascade, index, tracking |
| `sequence` | Integer | default 10 |
| `type` | Selection | document/software/migration/integration/training/other; required, default other |
| `description` | Text | — |
| `responsible_id` | Many2one (`res.users`) | default current user, tracking |
| `due_date` | Date | tracking |
| `state` | Selection | draft/submitted/accepted/rejected; required, default draft, tracking, copy=False |
| `submitted_by` | Many2one (`res.users`) | readonly, copy=False |
| `submitted_date` | Datetime | readonly, copy=False |
| `accepted_by` | Many2one (`res.users`) | readonly, copy=False |
| `accepted_date` | Datetime | readonly, copy=False |
| `rejected_by` | Many2one (`res.users`) | readonly, copy=False |
| `rejected_date` | Datetime | readonly, copy=False |
| `rejection_reason` | Text | tracking |
| `company_id` | Many2one (`res.company`) | related `project_id.company_id`, stored, readonly, index |
| `tag_ids` | Many2many (`amnus.tag`) | relation `amnus_project_deliverable_tag_rel` |
| `task_ids` | One2many (`project.task`) | inverse `amnus_deliverable_id` |
| `task_count` | Integer | computed |
| `active` | Boolean | default True |

Ordering: `project_id, sequence, id`.

### Why not `project.milestone`

A milestone is a dated progress marker with `is_reached`. A deliverable is a
contractual output with a type, an acceptance workflow, a recorded sign-off and a
rejection reason. They are complementary; no standard model is duplicated or
replaced.

## Project extension fields

| Field | Type | Attributes |
|-------|------|------------|
| `amnus_is_amnus_project` | Boolean | default False, index, copy=False |
| `amnus_request_id` | Many2one (`amnus.crm.project.request`) | ondelete=set null, index, copy=False, readonly |
| `amnus_request_type` | Selection | related stored (`amnus_request_id.request_type`), readonly |
| `amnus_actual_go_live` | Date | copy=False, tracking |
| `amnus_deliverable_ids` | One2many (`amnus.project.deliverable`) | inverse `project_id` |
| `amnus_deliverable_count` | Integer | computed |
| `amnus_tag_ids` | Many2many (`amnus.tag`) | relation `amnus_project_project_tag_rel` |

SQL constraint: `UNIQUE (amnus_request_id)` — at most one project per request.

Date semantics:

- planned start → standard `date_start`;
- planned go-live/end → standard `date` (Odoo labels it *Expiration Date*; with
  Odoo's SQL check `date >= date_start`, so plan the planned start first);
- actual go-live → `amnus_actual_go_live`.

## Task extension

| Field | Type | Attributes |
|-------|------|------------|
| `amnus_deliverable_id` | Many2one (`amnus.project.deliverable`) | ondelete=set null, index, copy=False, domain `[('project_id', '=', project_id)]` |

`@api.constrains('amnus_deliverable_id', 'project_id')` rejects any task whose
deliverable belongs to another project. Changing the task project or the
deliverable so that the link becomes inconsistent is rejected.

## CRM request extension

| Field | Type | Attributes |
|-------|------|------------|
| `project_id` | Many2one (`project.project`) | readonly, copy=False, ondelete=set null, index |
| `project_count` | Integer | computed (0/1) |

Constraints and guards:

- `@api.constrains('project_id')` requires `request.project_id.amnus_request_id == request`
  (consistency of both directions).
- `create` rejects any incoming `project_id`.
- `write` rejects direct RPC writes to `project_id` unless the environment is
  superuser (`self.env.su`, the trusted server-side boundary).

## Handover: `action_create_project()`

Preconditions, all server-side:

1. Caller is `amnus_projects.group_amnus_project_manager` or superuser.
2. `request.company_id` exists and is in `self.env.companies`.
3. `request.lead_id.company_id`, when set, matches the request company.
4. `request.partner_id` company matches the request company. A child contact
   without `company_id` is resolved through `commercial_partner_id.company_id`
   before deciding, so legitimate child contacts are accepted.
5. `SELECT state, project_id ... FOR UPDATE` locks the request row.
6. Re-checked under the lock: `state == 'approved'` and `project_id` is empty.

Then:

```
project.project.create({
    name:            lead.name or request.name,
    partner_id:      request.partner_id,
    user_id:         request.user_id or lead.user_id or current user,
    company_id:      request.company_id,
    date_start:      request.expected_start_date,
    date:            request.expected_go_live,
    description:     request.scope_summary or request.description,
    amnus_is_amnus_project: True,
    amnus_request_id:       request.id,
    amnus_tag_ids:          lead.amnus_tag_ids,
})
request.sudo().write({'project_id': project.id})
audit log event (action="create", model=project.project)
project.message_post(...)
return act_window(project.project, res_id=project.id)
```

No manual `commit()` is used: the handover is atomic with the surrounding
transaction. If audit logging or the message post fails, the project creation is
rolled back as well. The unique SQL constraint on `project.project.amnus_request_id`
is the second line of defense against concurrent handovers.

`project.project.create()` also synchronizes the request backlink when a project
is created through the ORM with `amnus_request_id`, and validates that the request
is approved, unlinked and in the same company.

`amnus_request_id` and `request.project_id` cannot be written directly through RPC
(only the handover and the create-sync use `sudo()`).

## Deliverable workflow

```
draft ──action_submit──▶ submitted ──action_accept──▶ accepted
  ▲                          │
  │                          └──action_reject──▶ rejected
  └────────── action_reset_to_draft ─────────────┘
```

### Transition authorization

| Transition | Allowed caller | Source state | Effects |
|------------|----------------|--------------|---------|
| Submit | responsible user or manager | draft, rejected | state=submitted; submitted_by/date; clears previous decision |
| Accept | manager only | submitted | state=accepted; accepted_by/date; clears rejection |
| Reject | manager only | submitted | state=rejected; rejected_by/date; requires non-empty reason |
| Reset to draft | manager only | submitted, rejected | state=draft; clears all sign-off fields |

Every transition writes an `amnus.audit.log` event with `action="state_change"`.

### Security boundary for ORM writes

- `create`: rejects a non-`draft` state and any sign-off field.
- `write` (non-superuser): rejects `state` and sign-off fields outright.
- Workflow methods perform authorization manually, then call `self.sudo().write()`.
- `self.env.su` is used as the boundary because context keys are client-controllable
  through RPC and are never trusted.
- Accepted deliverables: business fields (`name`, `project_id`, `type`,
  `description`, `responsible_id`, `due_date`, `tag_ids`, `active`) are frozen for
  non-managers; accepted records cannot be unlinked (archive instead).
- `project_id` cannot be changed after submission or while tasks are linked.
- `project.project.unlink()` refuses to delete a project containing accepted
  deliverables (archive the project instead).

Timestamps use `fields.Datetime.now()` and identities `self.env.user`, never
caller-provided values.

## Security

### Groups

| Group | XML ID | Implies |
|-------|--------|---------|
| AMNUS Project User | `amnus_projects.group_amnus_project_user` | `amnus_core.group_amnus_user`, `project.group_project_user`, `project.group_project_stages` |
| AMNUS Project Manager | `amnus_projects.group_amnus_project_manager` | project user, `project.group_project_manager` |
| AMNUS Project Administrator | `amnus_projects.group_amnus_project_admin` | project manager |

Groups are not assigned to any existing user on install. Standard Odoo groups
(including the `noupdate="1"` core groups) are referenced only; their implied
groups, ACLs and record rules are not modified.

### ACLs (`security/ir.model.access.csv`)

| Model | Group | Create | Read | Write | Unlink |
|-------|-------|--------|------|-------|--------|
| `amnus.project.deliverable` | AMNUS Project User | ✓ | ✓ | ✓ | — |
| `amnus.project.deliverable` | AMNUS Project Manager | ✓ | ✓ | ✓ | ✓ |
| `amnus.project.deliverable` | AMNUS Project Administrator | ✓ | ✓ | ✓ | ✓ |

Standard project ACLs are untouched: project users remain read-only on projects,
project managers keep standard CRUD.

### Record rules (`security/amnus_projects_security.xml`, `noupdate="1"`)

| Rule | Groups | Domain |
|------|--------|--------|
| Multi-company | global | `[('company_id', 'in', company_ids + [False])]` |
| Project visibility | AMNUS Project User | `employees/portal OR follower OR project manager OR deliverable responsible` |
| Manager all-rule | AMNUS Project Manager | `[(1, '=', 1)]` |

The visibility rule mirrors standard project/task visibility and applies only to
the custom deliverable model, so it never broadens access to standard projects.

## Views, actions and menus

- `project.project` form: deliverable smart button, request smart button, AMNUS
  flag, AMNUS tags, and an *AMNUS Implementation* group (request, request type,
  actual go-live).
- `project.project` search: *AMNUS Projects* filter and *AMNUS Request Type* group-by.
- `project.task` form: optional deliverable field, filtered to the task project.
- `project.task` search: *AMNUS Deliverable Tasks* filter.
- `amnus.project.deliverable`: list, form (status bar + workflow buttons, sign-off
  tab, chatter) and search views; window action with empty-state help.
- `amnus.crm.project.request`: *Create Project* / *View Project* buttons and an
  *Approved, Not Handed Over* search filter.
- AMNUS root → **Projects**: Projects, Deliverables, Configuration → Project Stages.

## Internationalization

All user-facing Python strings are wrapped in `_()`. XML strings are translatable
through Odoo's standard export. `i18n/amnus_projects.pot`, `i18n/fr_FR.po` and
`i18n/ar_SA.po` are provided. The UI uses standard Odoo widgets, which already
support RTL when the user language is Arabic.

## Tests

61 `at_install` tests, 0 failures, 0 errors:

| File | Tests | Coverage |
|------|-------|----------|
| `test_installation.py` | 6 | module/dependencies/models/views/menus, standard project compatibility |
| `test_project_integration.py` | 9 | fields, tags, request link, duplicate and state guards, counts, deletion protection |
| `test_crm_handover.py` | 10 | successful handover, audit, chatter, guards, company consistency, child contact, forged link, rollback |
| `test_deliverables.py` | 20 | defaults, guards, submit/accept/reject/reset, identity, lock, unlink, multi-record, task count |
| `test_task_integration.py` | 6 | link, unlinked task, cross-project rejection, relink consistency |
| `test_security.py` | 10 | group hierarchy, no auto-assignment, ACLs, company isolation, forged sign-off |

Run with:

```
odoo-bin -c <config> -d <test_db> -u amnus_projects --test-enable --test-tags amnus_projects --stop-after-init
```

Regression status at delivery: `amnus_core` 34/34 and `amnus_crm` 23/23 pass in
a fully loaded registry.

## Known limitations

- No automatic stage provisioning: the addon ships no stage data, by design.
- No chatter on `amnus.crm.project.request` (the model does not inherit
  `mail.thread`); the handover message is posted on the new project.
- Deliverables are not linked to `project.milestone` yet.
- A cancelled request does not cancel or delete its project; this is deliberate.
- Actual go-live is a single date, not a per-deliverable gate.

## Dependencies

- `amnus_core` — tags, audit log, groups, AMNUS root menu
- `amnus_crm` — `amnus.crm.project.request`
- `project` — standard project/task models
- `mail` — chatter

## Installation

Install `amnus_core`, `amnus_crm` and `project`, then install `amnus_projects`,
then explicitly assign the AMNUS project groups to users.
