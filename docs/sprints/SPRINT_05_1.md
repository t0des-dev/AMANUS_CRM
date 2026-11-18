# SPRINT 05.1 — Requirements Management

**Sprint:** 05.1 — Requirements Management  
**Status:** IMPLEMENTATION COMPLETE  
**Type:** Feature Implementation  
**Target Module:** `amnus_analysis`  
**Platform:** Odoo 19 Community Edition  
**Repository:** `C:\Users\PC\Desktop\workflow\ModuleOdoo19\amnus\`  
**Base Branch:** `main`  
**Base HEAD:** `0f206a5d80b5f421ae76c6b3b2833a591ffd694b`  
**Feature Branch:** `feature/sprint-05-1-amnus-analysis`  
**Test Database:** `amnus_test_19`

---

## 1. Objective

Implement the first Consulting Core capability of AMNUS: **Requirements Management**. This provides Odoo Implementation Partners with a structured way to discover, document, organize, review, approve, and trace customer business and functional requirements throughout an Odoo implementation project.

The module integrates with the existing AMNUS project foundation (`amnus_projects`) and preserves the established architectural separation between planning (requirements) and execution (`project.task`).

---

## 2. Functional Scope

### 2.1 Requirement Management (`amnus.analysis.requirement`)

Each requirement is a first-class record linked to an implementation project, supporting:

| Field | Type | Purpose |
|-------|------|---------|
| `reference` | Char (sequence) | Stable, human-readable requirement ID (e.g. `REQ-00001`) |
| `name` | Char | Requirement title |
| `description` | Text | Detailed requirement description |
| `requirement_type` | Selection | Business / Functional / Non-Functional |
| `priority` | Selection | Critical / High / Medium / Low |
| `business_value` | Text | Business value delivered |
| `source` | Selection | Workshop / Interview / Document / Email / Other |
| `acceptance_criteria` | Text | Criteria for implementation completion |
| `notes` | Text | Internal notes |
| `project_id` | Many2one (`project.project`) | Owning implementation project |
| `customer_id` | Many2one (`res.partner`) | Derived from project |
| `stakeholder_id` / `owner_id` / `analyst_id` | Many2one (`res.users`) | Responsible parties |
| `target_stage_id` | Many2one (`project.project.stage`) | Target project stage |
| `task_id` / `story_id` / `deliverable_id` | Many2one | Optional traceability links |
| `company_id` | Many2one (`res.company`) | Derived from project (multi-company) |
| `state` | Selection | Draft / Under Review / Approved / Rejected / Cancelled |
| `approved_by` / `approved_date` | Many2one / Datetime | Approval audit |
| `rejected_by` / `rejected_date` / `rejection_reason` | Many2one / Datetime / Text | Rejection audit |

### 2.2 Requirement Lifecycle

```
Draft --> Under Review --> Approved
   |          |              |
   +----------+--------------> Rejected
   |
   +----------------------> Cancelled
   Approved --> Under Review (controlled revision)
```

* Draft requirements can be edited by authorized analysts.
* Submission for review is explicit (`action_submit_for_review`).
* Approval requires AMNUS Analysis Manager authorization (`action_approve`).
* Rejection requires a reason (`action_reject`).
* Approved requirements cannot be silently rewritten; a controlled revision (`action_request_revision`) returns them to Under Review.
* Direct ORM state writes are rejected (`write()` guards).
* Approved/rejected requirements cannot be deleted (`unlink()` guard).

### 2.3 Workshops (`amnus.analysis.workshop`)

Structured discovery sessions supporting workshop reference, type, date/duration, location, facilitator, internal and customer participants, agenda, discussion notes, decisions, outcomes, follow-up actions, and related requirements.

### 2.4 AS-IS / TO-BE Processes (`amnus.analysis.process`)

Business process documentation supporting process reference, category, AS-IS description, TO-BE description, related requirements, owner, and status.

### 2.5 Requirement Prioritization

Priority classification: Critical / High / Medium / Low. Priority is distinct from approval state. Business value is recorded separately.

### 2.6 Requirement Traceability

Requirements can be linked to:
* `project.task` — implementation task (same project enforced)
* `amnus.agile.user.story` — Agile user story (same project enforced)
* `amnus.project.deliverable` — contractual deliverable (same project enforced)

All links enforce project and company consistency via ORM constraints. Cross-project and cross-company links are rejected.

### 2.7 Customer Review and Approval

Internal approval capability (submit for review, approve, reject with reason). Portal-based customer approval is explicitly out of scope for this Sprint. Internal analyst review is distinguished from Project Manager approval.

---

## 3. Explicit Exclusions

* Fit-Gap Analysis (`amnus_fitgap`) — future Sprint
* Scope & Change Management (`amnus_scope`) — future Sprint
* Data Migration (`amnus_migration`) — future Sprint
* Testing & QA (`amnus_qa`) — future Sprint
* Deployment & Go-Live (`amnus_devops`) — future Sprint
* Timesheets (`amnus_timesheets`) — folded into `amnus_projects`
* Documents (`amnus_documents`) — deferred (`documents` Community module absent)
* Support (`amnus_support`) — deferred (`helpdesk` Community module absent)
* Dashboard (`amnus_dashboard`) — folded into `amnus_projects`
* Development tasks (`amnus_development`) — folded into `amnus_projects`
* Portal-based customer approval — out of scope for this Sprint
* Visual BPMN process designer — out of scope

---

## 4. Data Model

| Model | XML ID | Purpose |
|-------|--------|---------|
| `amnus.analysis.requirement` | `model_amnus_analysis_requirement` | Requirement record with lifecycle |
| `amnus.analysis.workshop` | `model_amnus_analysis.workshop` | Discovery workshop |
| `amnus.analysis.process` | `model_amnus_analysis.process` | AS-IS / TO-BE process |

Database constraints:
* `unique (reference)` — requirement reference uniqueness
* `unique (reference)` — workshop reference uniqueness
* `unique (reference)` — process reference uniqueness
* ORM constraints enforce project/company consistency on task, story, and deliverable links

---

## 5. Workflow

| Action | From State | To State | Actor |
|--------|-----------|----------|-------|
| Submit for Review | Draft | Under Review | Analyst / Manager |
| Approve | Under Review | Approved | Manager |
| Reject | Under Review | Rejected | Manager (+ reason) |
| Cancel | Draft / Under Review | Cancelled | Analyst / Manager |
| Request Revision | Approved | Under Review | Manager |

---

## 6. Security

### 6.1 Groups

| Group | XML ID | Implies |
|-------|--------|---------|
| AMNUS Analysis User | `group_amnus_analysis_user` | `amnus_core.group_amnus_user` |
| AMNUS Analysis Manager | `group_amnus_analysis_manager` | analysis user, `amnus_projects.group_amnus_project_manager` |
| AMNUS Analysis Administrator | `group_amnus_analysis_admin` | analysis manager |

Groups are never auto-assigned.

### 6.2 ACLs

ACLs defined in `security/ir.model.access.csv` for requirement, workshop, and process models (create/read/write/unlink per user/manager/admin group).

### 6.3 Record Rules

Multi-company isolation (`company_id in company_ids + [False]`) and project visibility (mirroring standard project visibility) on all three models. Managers see all records in their allowed companies.

### 6.4 Workflow Authorization

Direct ORM state writes rejected. Workflow methods enforce `has_group()` authorization before `sudo().write()`. Approval/sign-off fields are never directly writable.

### 6.5 Audit

Significant lifecycle events (submission, approval, rejection, revision, cancellation) are written through `amnus.audit.log._log_event()`.

---

## 7. Module Dependencies

| Dependency | Purpose |
|------------|---------|
| `amnus_core` | Foundation, security groups, audit log, tags |
| `amnus_projects` | Project execution model, project visibility groups |
| `project` | Standard Odoo Project (execution model, reused) |
| `mail` | Chatter |

Dependency direction: `amnus_core` → `amnus_projects` → `amnus_analysis` (acyclic, downward only).

---

## 8. UI Implementation

Native Odoo 19 XML views (list, kanban, form, search) for requirements, workshops, and processes. Menus integrated under *AMNUS → Analysis*. No custom OWL. No custom JavaScript. No Enterprise-only widgets.

---

## 9. Test Results

### New module tests (`amnus_analysis`)

Run via Odoo's test runner (`odoo.tests.shell.run_tests`) on `amnus_test_19` (at_install, 42 tests discovered, 0 failures, 0 errors, all exit 0):

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `test_requirement.py` | 18 | Requirement creation, required fields, sequence generation, types, priorities, state transitions, approval/rejection, direct state-write bypass, controlled revision, cancel, unlink protection, task/story same-project, task/story cross-project rejection, approve requires manager, rejection reason tracking |
| `test_workshop.py` | 7 | Workshop creation, draft-only creation, mark held, cancel, unlink protection, requirement link, cross-project requirement rejection |
| `test_process.py` | 8 | Process creation, draft-only creation, state transitions, approve requires manager, cancel, unlink protection, requirement link, cross-project requirement rejection |
| `test_security.py` | 9 | Group hierarchy, groups not auto-assigned, user/manager ACLs, user cannot write state directly, user cannot approve, manager can approve, cross-company isolation, user sees own project requirements |

### Regression suites (sequential, one Odoo process at a time on `amnus_test_19`)

| Suite | Command | Exit | Total | Failed | Errors | Log |
|-------|---------|------|-------|--------|--------|-----|
| `amnus_core` | `-u amnus_core --test-enable --test-tags amnus_core --stop-after-init` | 0 | 34 | 0 | 0 | `%TEMP%\amnus_s051_reg_core.log` |
| `amnus_crm` | `-u amnus_crm --test-enable --test-tags amnus_crm --stop-after-init` | 0 | 23 | 0 | 0 | `%TEMP%\amnus_s051_reg_crm.log` |
| `amnus_projects` | `-u amnus_projects --test-enable --test-tags amnus_projects --stop-after-init` | 0 | 61 | 0 | 0 | `%TEMP%\amnus_s051_reg_projects.log` |
| `amnus_agile` | `-u amnus_agile --test-enable --test-tags amnus_agile --stop-after-init` | 0 | 98 | 0 | 0 | `%TEMP%\amnus_s051_reg_agile.log` |
| **Total** | | | **216** | **0** | **0** | |

**Combined total: 258 tests (42 new + 216 regression), 0 failures, 0 errors, all exit 0.**

---

## 10. Translation Results

| Catalog | Entries | Translated | Coverage | Odoo Reader | polib | MO Compile |
|---------|---------|------------|----------|-------------|-------|------------|
| `amnus_analysis.pot` | 164 | 0 (template) | n/a | OK | OK | n/a |
| `fr_FR.po` | 164 | 164 | 100.0% | OK | OK | OK |
| `ar_SA.po` | 164 | 164 | 100.0% | OK | OK | OK |

Arabic (ar_SA) relies on native Odoo web-client RTL behavior (no custom OWL/CSS in the module). Visual RTL review not performed in this Sprint.

---

## 11. Known Limitations

* Requirement references are globally unique (not project-scoped).
* Portal-based customer approval is out of scope.
* No visual BPMN process designer; process documentation is text-based.
* No automatic stage provisioning for target stages.
* Arabic RTL not visually reviewed (relies on native Odoo behavior).

---

## 12. Future Integration Points

* Fit-Gap (`amnus_fitgap`) — link gaps to requirements
* Scope & Change (`amnus_scope`) — change requests linked to requirements
* Implementation Planning (`amnus_development`, folded into `amnus_projects`) — WBS tasks linked to requirements
* Testing (`amnus_qa`) — test cases derived from requirements
* Deployment (`amnus_devops`) — go-live readiness tied to requirement coverage

---

## 13. Safety

* Only `amnus_test_19` used for database testing (`db_name`/`db_filter` verified before each command)
* No `-u all`
* No competing Odoo processes
* No Odoo core, legacy `amanus_*`, or Enterprise modifications
* No merge, push, reset, clean, stash, or history rewrite
* Pre-existing untracked audit reports preserved
