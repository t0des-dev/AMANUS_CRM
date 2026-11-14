# SPRINT 03 — DISCOVERY: `amnus_projects`

**Sprint:** 03 — Project Lifecycle Foundation
**Branch:** `feature/sprint-03-amnus-projects`
**Base commit:** `fa32ccc` (`main`, fast-forward merge of Sprint 02)
**Date:** 2026-11-14
**Scope:** Discovery and architecture proposal only. No addon code was written, no module was
installed or upgraded, and no database was modified.
**Recommendation:** **READY FOR IMPLEMENTATION** — see §12 for the single environment precondition.

---

## 1. Executive summary

`amnus_projects` is the AMNUS project-lifecycle addon. It must **extend** the standard Odoo 19
Community `project.project` and `project.task` models, never replace them. Its Sprint 03 job is to
turn an **approved CRM implementation request** into a real Odoo project, add the AMNUS lifecycle
metadata that Odoo does not provide, and introduce a light **deliverable** object for contractual
outputs and acceptance.

Verified conclusions:

- `project` is present in `odoo/addons` (Community) but **not installed** in `amnus_test_19`.
- `project` depends on `analytic`, `rating`, `resource`, `portal`, `mail`, `base_setup`,
  `web`, `web_tour`, `digest` — **no Enterprise module, no `sale`, no `hr_timesheet`, no `account`**.
- Odoo 19 already provides project stages (`project.project.stage`), task stages
  (`project.task.type`), task states, project health (`last_update_status`), milestones, tags and
  a full security/visibility model. `amnus_projects` must not duplicate any of them.
- `project.project.stage_id` is a **group-restricted field** (`project.group_project_stages`).
  AMNUS must explicitly enable that feature group for AMNUS project users, or stage-based lifecycle
  logic will be unavailable to them.
- Standard `project.project` ACL grants **read-only** to `project.group_project_user`; create/write
  requires `project.group_project_manager`. AMNUS project management therefore needs the standard
  manager group (implied by the new AMNUS project manager group).
- There is **no native `crm.lead` → `project.project` link** in Community. The handover must be
  custom and is the core of Sprint 03.
- Existing AMNUS groups are declared inside `<data noupdate="1">`, so `amnus_projects` **cannot**
  add `implied_ids` to them from XML. New AMNUS project groups are required.

---

## 2. Scope and non-goals

### In scope (proposed implementation)

1. Extend `project.project` with AMNUS lifecycle metadata and the CRM request link.
2. Extend `project.task` with an optional deliverable link.
3. New model `amnus.project.deliverable` (deliverable + acceptance tracking).
4. CRM → Projects handover: create a `project.project` from an **approved**
   `amnus.crm.project.request`, with field mapping, idempotency, permissions and audit logging.
5. AMNUS menus, actions, list/kanban/form/search views, inherited project/task/CRM-request views.
6. Security: groups, privilege, ACLs, company record rules, server-side transition guards.
7. i18n scaffolding (`fr_FR`, `ar_SA`), technical docs, tests.

### Explicit non-goals

- **No Scrum/agile** objects (sprints, backlog, velocity) — belongs to `amnus_agile`.
- **No new project or task model**, no replacement of `project.project`, `project.task`,
  `project.project.stage`, `project.task.type` or task `state` values.
- **No `sale` / quotation / invoicing** integration in Sprint 03 (see §7).
- **No timesheets** (`hr_timesheet`), no `account`/analytic accounting logic.
- **No portal-facing deliverable acceptance** in Sprint 03.
- **No installation, upgrade or data change** during discovery.

---

## 3. Verified environment and Git state

| Item | Verified value | How verified |
|------|----------------|--------------|
| Repository | `C:\Users\PC\Desktop\workflow\ModuleOdoo19\amnus` | working directory |
| Current branch | `feature/sprint-03-amnus-projects` | `git branch --show-current` |
| `main` HEAD | `fa32ccc feat(amnus_crm): implement AMNUS CRM foundation` | `git log --oneline -1` |
| Working tree | clean | `git status --short` |
| Odoo version | 19.0.0 (`version_info = (19, 0, 0, FINAL, 0, '')`) | `odoo/odoo/release.py` |
| Odoo addons path | `C:\Program Files\AmanusERP\odoo\addons` | `config/amnus-test.conf` |
| Test DB | `amnus_test_19` (PostgreSQL 16.14, port 55432) | `config/amnus-test.conf` |
| Python | 3.12.10 (`C:\Program Files\AmanusERP\python\python.exe`) | environment |

Database module states (queried in `amnus_test_19`, discovery read-only):

| Module | State | Relevance |
|--------|-------|-----------|
| `amnus_core` | installed | foundation |
| `amnus_crm` | installed | handover source |
| `crm` | installed | opportunities |
| `contacts`, `mail`, `portal`, `resource`, `base_setup`, `digest`, `web_tour` | installed | reused |
| `project` | **uninstalled** | target extension module |
| `analytic`, `rating` | uninstalled | pulled in by `project` |
| `sale`, `hr_timesheet`, `account`, `hr` | uninstalled | **not required** |

Sprint 02 is merged; `main` is at `fa32ccc` and the Sprint 03 branch was created from that exact
commit. `feature/sprint-02-amnus-crm` still exists locally and is not merged again.

---

## 4. Odoo 19 `project` module findings (verified from source)

### 4.1 Manifest and installation footprint

`odoo/addons/project/__manifest__.py`:

```python
'depends': [
    'analytic', 'base_setup', 'mail', 'portal', 'rating',
    'resource', 'web', 'web_tour', 'digest',
]
```

Transitive additions when installing `project` on `amnus_test_19`:
`analytic` → `base`, `mail`, `uom`; `rating` → `mail`. `digest`, `portal`, `resource`,
`base_setup`, `web`, `web_tour` are already installed. **`account` is not a dependency.**
`uom` must be verified at install time (expected to be available in Community).

### 4.2 Models

| Model | Purpose | Reuse decision |
|-------|---------|----------------|
| `project.project` | project header, customer, manager, dates, visibility, health, tags | **extend** (`_inherit`) |
| `project.task` | work items, assignees, deadlines, states, subtasks, tags | **extend** (`_inherit`) |
| `project.project.stage` | project lifecycle stages (`active`, `sequence`, `name`, `fold`, `company_id`, `color`, `mail_template_id`) | **reuse as-is** |
| `project.task.type` | per-project task stages | **reuse as-is** |
| `project.tags` | project/task tags (`name`, `color`, `project_ids`, `task_ids`) | **reuse for scheduling tags** |
| `project.milestone` | dated milestone marker (`name`, `project_id`, `deadline`, `is_reached`, `task_ids`) | **reuse later**; not the deliverable object |
| `project.update` | status updates feeding `last_update_status` | **reuse for project health** |

Verified `project.project` fields used by this sprint: `name`, `description`, `partner_id`,
`company_id` (computed + inverse), `user_id`, `date_start`, `date` (expiration/end),
`privacy_visibility` (default `portal`), `stage_id`, `tag_ids`, `last_update_status`,
`favorite_user_ids`, `is_template`, `active`, `sequence`.

Verified `project.task` fields relevant here: `name`, `project_id`, `user_ids`, `company_id`
(computed), `stage_id`, `state`, `date_deadline`, `tag_ids`, `milestone_id`, `child_ids`.

### 4.3 Lifecycle: stages and task states

- Default project stages (data, `noupdate`): `To Do` (10), `In Progress` (15), `Done` (20),
  `Cancelled` (25).
- `project.project.stage_id` is declared with `groups="project.group_project_stages"`.
  **The field does not exist for users outside that group** — this is the most important
  constraint in this discovery.
- `group_project_stages`, `group_project_milestone`, `group_project_task_dependencies` and
  `group_project_recurring_tasks` are plain feature groups with **no implied groups and no default
  users**. AMNUS must grant them explicitly.
- Task `state` values (server-computed, not freely writable):
  `01_in_progress`, `02_changes_requested`, `03_approved`, `1_done`, `1_canceled`,
  `04_waiting_normal`. `CLOSED_STATES = {'1_done', '1_canceled'}`.
- `project.project.last_update_status` provides project health:
  `on_track`, `at_risk`, `off_track`, `on_hold`, `to_define`, `done`.
  **No AMNUS health field is needed.**

### 4.4 Access control lists (`project/security/ir.model.access.csv`)

| Model | Group | C | R | W | U |
|-------|-------|---|---|---|---|
| `project.project` | `project.group_project_user` | – | ✓ | – | – |
| `project.project` | `project.group_project_manager` | ✓ | ✓ | ✓ | ✓ |
| `project.project` | `base.group_user` | – | ✓ | – | – |
| `project.project.stage` | `base.group_user` | – | ✓ | – | – |
| `project.project.stage` | `project.group_project_manager` | ✓ | ✓ | ✓ | ✓ |
| `project.task` | `project.group_project_user` | ✓ | ✓ | ✓ | ✓ |
| `project.task.type` | `project.group_project_user` | ✓ | ✓ | ✓ | ✓ |

Consequence: an AMNUS user who only has `amnus_core.group_amnus_user` **cannot create or edit
projects**. Sprint 03 therefore introduces an AMNUS project manager group that implies
`project.group_project_manager`.

### 4.5 Record rules, multi-company and visibility

- `project_comp_rule`: `[('company_id', 'in', company_ids + [False])]` — global (no group).
- `project_project_stage_rule`: same company domain.
- `project_project_manager_rule`: `[(1, '=', 1)]` for `group_project_manager` (sees every project
  **within the allowed companies**, because the global company rule still applies).
- `project_public_members_rule`: employees see projects whose visibility is `employees`/`portal`,
  or that they follow.
- `task_comp_rule`: `[('company_id', 'in', company_ids + [False])]`.
- Task visibility: employees see tasks of visible projects, tasks they follow, or tasks assigned
  to them; managers see all project tasks.
- Default `privacy_visibility` is `portal` (“All internal users and invited portal users”), so
  company-visible projects are readable by all internal users by default.

### 4.6 View and menu anchors verified

| XML ID | Use |
|--------|-----|
| `project.edit_project` | project form (`header`, `stage_id`, notebook pages `description`, `settings`) |
| `project.view_project` | project list view |
| `project.project_view_kanban` | project kanban view |
| `project.view_project_project_filter` | project search view (has filter `own_projects`) |
| `project.view_task_form2` | task form (`notebook` at line 463, page `extra_info`) |
| `project.view_task_search_form_project_base` | task search base view |
| `project.open_view_project_all` | “Projects” action (kanban,list,form) |
| `project.project_project_stage_configure` | project stages configuration action |
| `project.menu_main_pm`, `project.menu_projects` | standard Project app menus |
| `amnus_crm.view_amnus_crm_project_request_form` | handover UI anchor |
| `amnus_crm.action_amnus_crm_project_request` | request action |
| `amnus_core.menu_amnus_root`, `menu_amnus_configuration` | AMNUS menu roots |

---

## 5. Existing AMNUS APIs reused

### `amnus_core`

- Groups: `group_amnus_user` ← `group_amnus_manager` ← `group_amnus_admin`.
- `amnus.tag`: platform-wide classification, reusable on projects and deliverables.
- `amnus.audit.log._log_event(name, action, description, model_name, record_id)`:
  creates the trail entry with `sudo()`, derives user/company from the environment, and is
  immutable (`write`/`unlink` raise `AccessError`).
- Root menu `menu_amnus_root` and `menu_amnus_configuration`.

### `amnus_crm`

- `crm.lead` AMNUS fields: `amnus_is_implementation`, `amnus_request_type`,
  `amnus_project_summary`, `amnus_current_system`, `amnus_expected_start_date`,
  `amnus_expected_go_live`, `amnus_estimated_users`, `amnus_company_size`,
  `amnus_technical_notes`, `amnus_tag_ids`.
- `amnus.crm.project.request`: `name`, `lead_id` (required, cascade), `partner_id`/`contact_id`
  (stored related to `lead_id.partner_id`), `request_type`, `description`, `scope_summary`,
  `expected_start_date`, `expected_go_live`, `estimated_users`, `state`
  (`draft/submitted/reviewed/approved/rejected/cancelled`), `company_id`, `user_id`, `notes`.
- Workflow: `action_submit`, `action_review`, `action_approve`, `action_reject`, `action_cancel`.
  Approve/reject require `amnus_core.group_amnus_manager`; submit/approve are audit-logged.
- ACL: AMNUS user create/read/write (no unlink), manager/admin full; company record rule
  `[('company_id','in',company_ids)]` or `False`.

The handover must **reuse** `amnus.crm.project.request`; it must not create a second request model.

---

## 6. Proposed architecture for `amnus_projects`

### 6.1 Manifest

```python
{
    "name": "AMNUS Projects",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "AMNUS Project Lifecycle Management",
    "author": "AMNUS",
    "license": "LGPL-3",
    "depends": ["amnus_core", "amnus_crm", "project", "mail"],
    "data": [
        "security/amnus_projects_groups.xml",
        "security/amnus_projects_security.xml",
        "security/ir.model.access.csv",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/amnus_project_deliverable_views.xml",
        "views/amnus_crm_project_request_views.xml",
        "views/amnus_projects_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

`project` is a direct dependency even though `amnus_crm` does not depend on it. `mail` is declared
because the addon posts to project/request chatter. `analytic`, `rating`, `portal`, `resource`,
`web`, `web_tour`, `digest` come transitively and are **not** declared (we do not use them
directly).

### 6.2 Proposed file tree

```
addons/amnus/amnus_projects/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── project_project.py
│   ├── project_task.py
│   ├── amnus_project_deliverable.py
│   └── amnus_crm_project_request.py
├── security/
│   ├── amnus_projects_groups.xml
│   ├── amnus_projects_security.xml
│   └── ir.model.access.csv
├── views/
│   ├── project_project_views.xml
│   ├── project_task_views.xml
│   ├── amnus_project_deliverable_views.xml
│   ├── amnus_crm_project_request_views.xml
│   └── amnus_projects_menus.xml
├── i18n/
│   ├── amnus_projects.pot
│   ├── fr_FR.po
│   └── ar_SA.po
├── tests/
│   ├── __init__.py
│   ├── test_installation.py
│   ├── test_project_handover.py
│   ├── test_deliverable.py
│   └── test_security.py
├── static/description/index.html
└── README.md
```

### 6.3 Models and fields

#### `project.project` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `amnus_is_amnus_project` | Boolean, default `False`, index | flags AMNUS-managed projects; set automatically when a request is linked; allows manual AMNUS projects without a CRM request |
| `amnus_request_id` | Many2one `amnus.crm.project.request`, `ondelete='set null'`, index, `copy=False` | origin request; one project per request (enforced in code) |
| `amnus_request_type` | Selection, related `amnus_request_id.request_type`, stored, readonly | reporting/grouping without joining |
| `amnus_actual_go_live` | Date, `copy=False`, tracking | gate actually passed; distinct from planned `date` |
| `amnus_deliverable_ids` | One2many `amnus.project.deliverable`, `project_id` | deliverables |
| `amnus_deliverable_count` | Integer, computed | smart button |
| `amnus_tag_ids` | Many2many `amnus.tag` (`amnus_project_project_tag_rel`) | platform classification carried from `lead_id.amnus_tag_ids` |

Explicit reuse decisions:

- Planned start → standard `date_start`; planned go-live/end → standard `date`.
- Health → standard `last_update_status`; **no** `amnus_health` field.
- Lifecycle → standard `stage_id`; **no** `amnus_state` / `amnus_phase` field.
- Scheduling tags → standard `tag_ids`; AMNUS tags remain a separate platform taxonomy
  (`amnus.tag`), already used on `crm.lead`.

#### `project.task` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `amnus_deliverable_id` | Many2one `amnus.project.deliverable`, `ondelete='set null'`, index, `copy=False` | optional link of a task to the deliverable it contributes to |

Task `state`, `stage_id`, `user_ids`, `date_deadline` and `milestone_id` are **not** redefined.

#### `amnus.project.deliverable` (new)

| Field | Type | Notes |
|-------|------|-------|
| `name` | Char, required, tracking | deliverable title |
| `project_id` | Many2one `project.project`, required, `ondelete='cascade'`, index | owner project |
| `sequence` | Integer, default 10 | ordering |
| `deliverable_type` | Selection: `document`, `software`, `migration`, `integration`, `training`, `other`; required, default `other` | classification |
| `description` | Html | scope/acceptance criteria |
| `user_id` | Many2one `res.users`, default current user | responsible |
| `due_date` | Date | contractual due date |
| `acceptance_state` | Selection: `draft`, `submitted`, `accepted`, `rejected`; required, default `draft`, tracking | acceptance workflow |
| `submitted_date` | Date, readonly | set on submit |
| `accepted_date` | Date, readonly | set on accept |
| `accepted_by_id` | Many2one `res.users`, readonly | who signed off |
| `rejection_reason` | Text | required when rejecting |
| `tag_ids` | Many2many `amnus.tag` (`amnus_project_deliverable_tag_rel`) | platform classification |
| `company_id` | Many2one `res.company`, related `project_id.company_id`, stored, readonly, index | enables company rule |
| `active` | Boolean, default `True` | archive instead of delete |
| `task_ids` | One2many `project.task`, `amnus_deliverable_id` | contributing tasks |

Methods: `action_submit`, `action_accept`, `action_reject`, `action_reset_to_draft` with
server-side guards and audit entries. Acceptance/rejection is proposed as
**AMNUS project manager only** (see Q4). Deleting an accepted deliverable is denied.

Why not `project.milestone`: a milestone is a dated marker with `is_reached` and task links; it
has no type, acceptance workflow, sign-off fields or rejection reason. A deliverable is a
contractual output. They are complementary and can be linked in a later sprint (after
`project.group_project_milestone` is enabled), but a deliverable is **not** a renamed milestone.

#### `amnus.crm.project.request` (inherited)

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | Many2one `project.project`, readonly, `copy=False`, `ondelete='set null'`, index | created project |
| `project_count` | Integer, computed | smart button (0/1) |

Methods:

- `action_create_project()` — creates the project, writes `project_id`, logs the audit event,
  posts a message on both records, returns an `ir.actions.act_window` opening the new project.
- `action_view_project()` — opens the linked project.

### 6.4 CRM → Projects handover

Preconditions enforced server-side inside `action_create_project()`:

1. Request `state == 'approved'` (otherwise `UserError`).
2. Request has no `project_id` (idempotency; otherwise `UserError`).
3. Caller is `amnus_projects.group_amnus_project_manager` or superuser.
4. `request.company_id` is in `self.env.companies`; the company is allowed by the caller.
5. `request.partner_id` and `request.partner_id.company_id` do not contradict the request company;
   otherwise `UserError` with a clear message.

Field mapping:

| `project.project` | Source |
|-------------------|--------|
| `name` | `request.lead_id.name` (fallback: `request.name`) |
| `partner_id` | `request.partner_id` |
| `user_id` | `request.user_id` (fallback: `request.lead_id.user_id`, then current user) |
| `company_id` | `request.company_id` |
| `date_start` | `request.expected_start_date` |
| `date` | `request.expected_go_live` |
| `description` | `request.scope_summary` or `request.description` |
| `amnus_request_id` | `request` |
| `amnus_is_amnus_project` | `True` |
| `amnus_request_type` | computed from the link |
| `amnus_tag_ids` | `request.lead_id.amnus_tag_ids` |
| `privacy_visibility` | not set → standard default `portal` |
| `stage_id` | not set → standard default stage |

Flow:

```
amnus.crm.project.request (approved)
        │  "Create Project" button (manager only)
        ▼
action_create_project()
  ├─ guards (state / not linked / group / company)
  ├─ project.project.create(mapped values)
  ├─ request.project_id = project
  ├─ amnus.audit.log._log_event(action="create")
  ├─ request.message_post(...) + project.message_post(...)
  └─ return act_window(project.project, res_id=project.id)
```

Rejected/cancelled requests can never create a project. If a request is cancelled **after**
handover, the project is kept (no automatic deletion) and the situation is recorded in the
chatter; this is deliberate to avoid destroying work.

Button visibility in the request form: `state == 'approved'` and `not project_id`, restricted to
`amnus_projects.group_amnus_project_manager`. Server-side guards remain authoritative.

### 6.5 Lifecycle decision (no duplicated states)

- **Project lifecycle = `project.project.stage`**, the standard model. AMNUS does **not** add a
  stage model and does **not** add a parallel state selection.
- **Task lifecycle = `project.task.state` + `project.task.type`**, untouched.
- AMNUS ships **no** `project.project.stage` data records in Sprint 03. Reason: stages are
  company-level configuration; loading AMNUS stages next to the four standard stages would
  pollute every non-AMNUS project in the database, and `project_data.xml` records are `noupdate`.
  The recommended configuration is documented for administrators instead:

  | Recommended AMNUS stage | Standard stage it can replace | `fold` |
  |-------------------------|-------------------------------|--------|
  | Initiation | To Do | no |
  | Analysis | To Do | no |
  | Development | In Progress | no |
  | Testing / UAT | In Progress | no |
  | Deployment | In Progress | no |
  | Hypercare | Done | no |
  | Closed | Done / Cancelled | yes |

  An AMNUS configuration menu links to the standard stage configuration action
  (`project.project_project_stage_configure`).
- Because `stage_id` is group-restricted, the AMNUS project user and manager groups **imply**
  `project.group_project_stages`. This is an explicit, documented feature decision: AMNUS treats
  stages as the lifecycle, so AMNUS project users must have the stage feature enabled.

### 6.6 Views, actions and menus

| Element | Detail |
|---------|--------|
| Project form | inherit `project.edit_project`; add page `amnus` after `page[@name='settings']` with request link, request type, actual go-live, AMNUS tags, deliverables |
| Project form header/stat | smart buttons: “Request” (`action_view_request` on project), “Deliverables” (`action_view_deliverables`) |
| Project list (AMNUS) | own list view with name, customer, manager, stage, request type, actual go-live |
| Project kanban (AMNUS) | own kanban grouped by `stage_id`, with AMNUS-specific fields |
| Project search | inherit `project.view_project_project_filter`: filter “AMNUS Projects”, group by request type and actual go-live |
| Task form | inherit `project.view_task_form2`; add page `amnus` with `amnus_deliverable_id` (domain `[('project_id','=',project_id)]`) |
| Task list/search | add optional deliverable column/filter |
| Deliverable | list, kanban (grouped by acceptance state), form with statusbar and buttons, search |
| CRM request form | inherit `amnus_crm.view_amnus_crm_project_request_form`; add “Create Project” (primary, manager, approved, unlinked), “Open Project”, `project_id` |
| AMNUS menu | `menu_amnus_projects` under `amnus_core.menu_amnus_root`, sequence 16, groups `group_amnus_project_user`: “Projects”, “Deliverables” |
| AMNUS config menu | `menu_amnus_projects_config` under `amnus_core.menu_amnus_configuration`, sequence 15, manager: “Project Stages” → standard stage action |

Menu visibility uses the new AMNUS project groups, so the menus are not shown to unrelated AMNUS
users who were not granted project access.

No standard menu is modified or removed. The standard Project app remains available for users who
have the standard project groups; the AMNUS menu is an AMNUS-scoped entry point.

### 6.7 Security design

#### Groups and privilege (Odoo 19 style)

`security/amnus_projects_groups.xml`:

```xml
<record id="res_groups_privilege_amnus_projects" model="res.groups.privilege">
    <field name="name">AMNUS Projects</field>
    <field name="sequence">10</field>
</record>

<record id="group_amnus_project_user" model="res.groups">
    <field name="name">User</field>
    <field name="privilege_id" ref="res_groups_privilege_amnus_projects"/>
    <field name="implied_ids" eval="[
        (4, ref('amnus_core.group_amnus_user')),
        (4, ref('project.group_project_user')),
        (4, ref('project.group_project_stages')),
    ]"/>
</record>

<record id="group_amnus_project_manager" model="res.groups">
    <field name="name">Manager</field>
    <field name="privilege_id" ref="res_groups_privilege_amnus_projects"/>
    <field name="implied_ids" eval="[(4, ref('group_amnus_project_user')),
                                    (4, ref('project.group_project_manager'))]"/>
    <field name="user_ids" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
</record>
```

Rationale:

- Do **not** use `category_id` — Odoo 19 replaced it with `res.groups.privilege`.
- Do **not** attempt to add `implied_ids` to `amnus_core` groups from this addon: those records
  live in `<data noupdate="1">` and the update would be skipped. New groups are the safe path.
- The manager group implies the standard project manager group, which is required to create/edit
  `project.project` (standard ACL is read-only for project users).
- Group records are intentionally **not** `noupdate`, so future `implied_ids` corrections apply on
  upgrade. Record rules and ACLs follow the existing AMNUS pattern.

#### ACLs (`security/ir.model.access.csv`)

| Model | Group | C | R | W | U |
|-------|-------|---|---|---|---|
| `amnus.project.deliverable` | `group_amnus_project_user` | ✓ | ✓ | ✓ | – |
| `amnus.project.deliverable` | `group_amnus_project_manager` | ✓ | ✓ | ✓ | ✓ |

No new ACL is needed for `project.project`, `project.task` or `amnus.crm.project.request`: their
ACLs already exist and are inherited by the extension fields.

#### Record rules (`security/amnus_projects_security.xml`)

- `rule_amnus_project_deliverable_company`:
  `['|', ('company_id','=',False), ('company_id','in',company_ids)]` for the three AMNUS groups;
  `perm_unlink=False` for non-managers.
- No extra rule on `project.project` / `project.task`: the standard multi-company and visibility
  rules already apply. Adding an AMNUS-only rule with `[(1,'=',1)]` would **loosen** standard
  visibility and is explicitly rejected.

#### Server-side guards

- `action_create_project`: state, idempotency, group, company, partner/company consistency.
- Deliverable transitions: allowed source states only; accept/reject manager-only; rejection
  requires a reason; accepted deliverables are not unlinkable by non-admin.
- No `sudo()` except through the existing, documented `amnus.audit.log._log_event()`.

### 6.8 Multi-company behaviour

- Project company comes from `company_id` mapping or standard computation
  (`account_id.company_id` → `partner_id.company_id` → current company). The handover passes
  `request.company_id` explicitly and rejects contradictions.
- Deliverable company is a stored related of `project_id.company_id`, so the company rule is
  exact and cannot drift.
- CRM request company rule and standard project company rule remain in force; no cross-company
  read path is introduced.
- `amnus.audit.log` records the **current** company of the caller, which may differ from the
  project company when an admin acts across companies; the description includes the record id and
  reference. This matches the existing CRM behaviour and is accepted.

### 6.9 Audit

| Event | Action value | Source |
|-------|--------------|--------|
| Project created from CRM request | `create` | `action_create_project` |
| Deliverable submitted | `state_change` | `action_submit` |
| Deliverable accepted | `state_change` | `action_accept` |
| Deliverable rejected | `state_change` | `action_reject` |
| Deliverable reset to draft | `state_change` | `action_reset_to_draft` |

Every entry names `model_name` and `record_id` and includes the human reference (`request.name`
or deliverable `name`). The audit log remains read-only for manager/admin.

### 6.10 i18n and RTL

- All user-facing strings are `_()`-wrapped.
- Ship `i18n/amnus_projects.pot`, `fr_FR.po`, `ar_SA.po` for menus, fields, buttons, errors and
  help texts.
- The addon adds only standard XML views (no OWL/CSS), so RTL inherits Odoo’s standard RTL
  handling. Arabic strings still need **native review** before being considered final.

---

## 7. Dependency map and decisions

### AMNUS chain

```
amnus_core  ←  amnus_crm  ←  amnus_projects
                                  │
                                  └── project (Odoo Community)
```

- `amnus_projects` depends on `amnus_core` (tags, audit, groups, root menu) and `amnus_crm`
  (request model, lead fields, request workflow).
- No reverse dependency: `amnus_crm` does **not** depend on `amnus_projects`. The handover lives
  entirely in `amnus_projects` via `_inherit` of `amnus.crm.project.request`, so the CRM addon
  stays installable without `project`.
- Future addons (`amnus_agile`, `amnus_analysis`, `amnus_qa`, …) depend on
  `amnus_projects`, never the other way round.

### Odoo dependencies

| Module | Decision | Reason |
|--------|----------|--------|
| `project` | **required** | target of the extension; provides project/task/stages/security |
| `mail` | **required** | chatter on projects, requests, deliverables |
| `analytic` | transitive only | pulled by `project`; no AMNUS analytic logic |
| `rating` | transitive only | pulled by `project`; no customer rating in scope |
| `portal`, `resource`, `web`, `web_tour`, `digest` | transitive only | already installed / standard |
| `sale` | **not added** | no quotation, order or invoicing logic; would pull `account`/`product`/payment stack without a Sprint 03 need |
| `hr_timesheet` | **not added** | timesheets belong to `amnus_timesheets` |
| `account` | **not added** | no accounting requirement |

Adding `sale` later is a manifest-only change and is not blocked by this design.

### Documentation corrections required

- `docs/architecture/dependency_matrix.md` currently lists `project, sale` for `amnus_projects`
  and marks it verified. It must be corrected to `project` (with `sale` deferred).
- `docs/architecture/addons_architecture.md` lists `sale` for `amnus_projects`; same correction.
- These are documentation-only edits on the Sprint 03 branch; no addon code is touched.

---

## 8. Implementation plan (next sprint step, after approval)

1. **Approval gate** — obtain explicit approval to install `project` (and transitive `analytic`,
   `rating`, `uom` if needed) in `amnus_test_19`. No other database is touched.
2. **Scaffold addon** — manifest, `__init__.py`, folder tree, README, static description.
3. **Security first** — privilege, groups, ACL CSV, company rule. Verify group implication and
   that non-managers cannot create projects or accept deliverables.
4. **Models** — deliverable model and transitions; `project.project`, `project.task`,
   `amnus.crm.project.request` extensions; handover method with all guards.
5. **Views/actions/menus** — project, task, deliverable, CRM request inheritance, AMNUS menus.
6. **i18n** — `.pot`, `fr_FR.po`, `ar_SA.po` (Arabic marked for native review).
7. **Tests** — the plan in §9; run `amnus_projects`, then regress `amnus_core` and `amnus_crm`.
8. **Docs** — `docs/technical/amnus_projects.md`, `ADR-003` (reuse standard project models and
   CRM handover), dependency matrix/architecture corrections, `CHANGELOG.md`, `README.md`.
9. **Commit** on `feature/sprint-03-amnus-projects` with `feat(amnus_projects): ...`.
   **Do not merge to `main`** until architecture review and approval.

Suggested test command (after approval):

```powershell
& "C:\Program Files\AmanusERP\python\python.exe" `
  "C:\Program Files\AmanusERP\odoo\odoo-bin" `
  -c config\amnus-test.conf --test-enable --stop-after-init -u amnus_projects
```

---

## 9. Test plan (target ≈ 28–32 `at_install` tests)

| File | Coverage |
|------|----------|
| `test_installation.py` | module installed; dependencies loaded; models and fields exist; groups exist and imply the standard project groups |
| `test_project_handover.py` | approved request → project created with exact field mapping; `project_id` written back; audit entry created; second call rejected; draft/submitted/reviewed/rejected/cancelled requests rejected; non-manager rejected; cross-company request rejected; project `date_start`/`date`/`partner_id`/`user_id` correct; AMNUS tags copied |
| `test_deliverable.py` | create with defaults; company derived from project; submit → submitted; accept sets date/user and audit; reject requires reason and audit; invalid transitions rejected; accepted deliverable cannot be reset/unlinked by non-manager; task link domain and cardinality; archive behaviour |
| `test_security.py` | AMNUS project user cannot accept deliverables or create projects; project manager can; company rule hides other-company deliverables; ACL CSV grants match the design; standard project visibility rules are not loosened |

Regression gates: `amnus_core` 34 tests and `amnus_crm` 23 tests must stay green. Add a check that
`project` installs cleanly in a **fresh** test DB if feasible; otherwise document the manual check.

---

## 10. Risks and mitigations

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | `project` is uninstalled; runtime behaviour (default stage, computed company, install footprint) is verified from source only, not executed | **High** | Explicit approval to install `project` in the dedicated test DB; verify immediately after install; rollback plan is a DB backup |
| R2 | `stage_id` is group-restricted; users without `project.group_project_stages` cannot see the lifecycle | **High** | AMNUS project user/manager groups imply the stage group; test the field with a non-manager user |
| R3 | Standard project-user ACL is read-only; AMNUS users cannot create/edit projects | **High** | Manager group implies `project.group_project_manager`; handover restricted to manager; document role assignment |
| R4 | AMNUS core groups use `noupdate="1"`, so implied groups cannot be injected from `amnus_projects` | Medium | New dedicated project groups + documented assignment; revisit core group policy in a later sprint |
| R5 | Request company, lead company and partner company may disagree | Medium | Server-side consistency guard with explicit error; no silent reassignment |
| R6 | `amnus.tag` vs `project.tags` looks like duplicated classification | Low | Document the two taxonomies; AMNUS tags are platform classification, project tags are scheduling tags; both are reused, neither is redefined |
| R7 | Deliverables could be confused with `project.milestone` | Low | ADR records the distinction; milestone linking deferred until the feature group is enabled |
| R8 | Project install adds `analytic`/`rating` data and menus unrelated to AMNUS | Low | Transitive dependencies only; no AMNUS logic on them; document in the technical doc |
| R9 | Arabic translations and RTL layout unverified | Low | Ship `.po` files marked “pending native review”; no custom CSS/OWL to break RTL |
| R10 | One request → one project assumption may be too strict | Low | Enforced in Sprint 03 with a clear error; relaxing to 1:N later is a non-breaking change |

---

## 11. Open questions (need product/architecture answers before or during implementation)

1. **Group assignment strategy** — should every `amnus_core.group_amnus_user` automatically receive
   `group_amnus_project_user`, or is explicit assignment acceptable? Automatic assignment requires
   either removing `noupdate` from the core group records or a migration hook; both need approval.
2. **AMNUS stages** — confirm that Sprint 03 ships **no** stage data and relies on administrator
   configuration (recommended). If the business wants a ready-made AMNUS lifecycle, a later
   controlled data file can be approved.
3. **Go-live semantics** — confirm that planned go-live maps to the standard project `date`
   (Expiration Date) and that only the actual go-live gets an AMNUS field.
4. **Deliverable sign-off** — is acceptance restricted to the AMNUS project manager, or should the
   responsible user be allowed to accept? Current proposal: manager only.
5. **Cardinality** — confirm one project per implementation request (current proposal). Multiple
   projects per request would need a different link (One2many).
6. **Portal** — should customers see deliverables/acceptance in the portal in a later sprint?
   Out of scope now, but it influences field/state naming.
7. **`sale`** — confirm that commercial quotations/invoicing are out of scope for this phase.

---

## 12. Recommendation

**READY FOR IMPLEMENTATION.**

The architecture is fully verified against the Odoo 19 Community source and against the existing
`amnus_core` / `amnus_crm` APIs. No design blocker was found, and the addon can be implemented
without touching core, `amanus_*`, `business_starter_*`, production configuration or existing
business databases.

**Single environment precondition:** implementation verification requires explicit approval to
install `project` (with transitive `analytic`, `rating`, and `uom` if missing) in the dedicated
test database `amnus_test_19`. Until that approval is granted, code can be written and statically
reviewed, but the runtime test gate cannot be completed. This is an approval gate, not a design
blocker.

**Not blocked:** discovery, architecture review, documentation, and code scaffolding.

**Explicitly not done in Sprint 03 discovery:** no addon code, no module installation/upgrade, no
database writes, no merge to `main`.

---

## Appendix A — Evidence log

| # | Evidence | Source |
|---|----------|--------|
| 1 | Git branch `feature/sprint-03-amnus-projects`, HEAD `fa32ccc`, clean tree | `git branch --show-current`, `git log --oneline`, `git status --short` |
| 2 | Odoo 19.0.0 | `C:\Program Files\AmanusERP\odoo\odoo\release.py` |
| 3 | `project` manifest dependencies | `odoo/addons/project/__manifest__.py` |
| 4 | `analytic`, `rating`, `digest`, `web_tour`, `resource` manifests | `odoo/addons/<module>/__manifest__.py` |
| 5 | Project/task field definitions | `odoo/addons/project/models/project_project.py`, `project_task.py` |
| 6 | Stage model and default stages | `project/models/project_project_stage.py`, `project/data/project_data.xml` |
| 7 | Task `CLOSED_STATES` and `state` selection | `project/models/project_task.py` lines 84–93, 170–175 |
| 8 | Project/task/stage ACLs | `project/security/ir.model.access.csv` |
| 9 | Groups, company and visibility rules | `project/security/project_security.xml` |
| 10 | `group_project_stages` has no implied/default users | `project/security/project_security.xml` lines 24–41 |
| 11 | View/menu XML IDs and anchors | `project/views/project_project_views.xml`, `project_task_views.xml`, `project_menus.xml` |
| 12 | `project.project.last_update_status` and `project.milestone` fields | `project/models/project_project.py`, `project_milestone.py` |
| 13 | Odoo 19 `res.groups.privilege` fields | `odoo/odoo/addons/base/models/res_groups_privilege.py`, `res_groups.py` |
| 14 | AMNUS core groups/audit API/menu | `amnus_core/security/security.xml`, `models/amnus_audit_log.py`, `views/amnus_menu.xml` |
| 15 | CRM request model, workflow, views, ACL, rule | `amnus_crm/models/amnus_crm_project_request.py`, `views/amnus_crm_project_request_views.xml`, `security/*` |
| 16 | CRM lead AMNUS fields and `crm.lead` mapping fields | `amnus_crm/models/crm_lead.py`, `odoo/addons/crm/models/crm_lead.py` |
| 17 | Module states in `amnus_test_19` | read-only `psql` query on `ir_module_module` |
| 18 | Test configuration | `config/amnus-test.conf` (secrets redacted) |

## Appendix B — Documentation to update during implementation

| File | Change |
|------|--------|
| `docs/technical/amnus_projects.md` | new — models, fields, handover, lifecycle, security |
| `docs/architecture/ADRs/ADR-003-project-foundation.md` | new — extend standard project models; CRM handover; no Scrum |
| `docs/architecture/dependency_matrix.md` | `amnus_projects` Odoo deps: `project` only; `sale` deferred; status updated |
| `docs/architecture/addons_architecture.md` | `amnus_projects` deps corrected; status “Discovery (Sprint 03)” |
| `CHANGELOG.md` | Sprint 03 entry |
| `README.md` | addon table/status |
| `docs/sprints/SPRINT_03.md` | sprint record once implementation is complete |
