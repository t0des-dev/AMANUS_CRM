# AMNUS CRM — Technical Documentation

## Overview
`amnus_crm` extends standard Odoo 19 CRM with AMNUS-specific fields and provides
a structured implementation request model for formal project handover.

## Module manifest
- Name: AMNUS CRM
- Version: 19.0.1.0.0
- Category: Sales/CRM
- License: LGPL-3
- Depends: `amnus_core`, `crm`, `contacts`, `mail`
- Application: True
- Installable: True
- Auto install: False

## Reused standard Odoo models
- `crm.lead` — extended (not replaced) with AMNUS fields
- `res.partner` — used for customers and contacts
- Standard CRM stages, pipelines, activities, chatter

## Custom models
### amnus.crm.project.request
| Field | Type | Attributes |
|-------|------|------------|
| name | Char | required, readonly, sequence-generated |
| lead_id | Many2one (crm.lead) | required, ondelete=cascade |
| partner_id | Many2one (res.partner) | related to lead_id.partner_id, store=True |
| contact_id | Many2one (res.partner) | related to lead_id.partner_id, store=True |
| request_type | Selection | new_implementation/customization/migration/integration/support/training/consulting/other |
| description | Text | — |
| scope_summary | Text | — |
| expected_start_date | Date | — |
| expected_go_live | Date | — |
| estimated_users | Integer | default 0 |
| state | Selection | draft/submitted/reviewed/approved/rejected/cancelled |
| company_id | Many2one (res.company) | required, default current |
| user_id | Many2one (res.users) | default current |
| notes | Text | — |

### crm.lead (inherited)
AMNUS-specific fields added:
- `amnus_is_implementation` (Boolean)
- `amnus_request_type` (Selection)
- `amnus_project_summary` (Text)
- `amnus_current_system` (Char)
- `amnus_expected_start_date` (Date)
- `amnus_expected_go_live` (Date)
- `amnus_estimated_users` (Integer)
- `amnus_company_size` (Selection)
- `amnus_technical_notes` (Text)
- `amnus_tag_ids` (Many2many to amnus.tag)

## Workflow (implementation request)
```
draft → submitted → reviewed → approved
                            → rejected
draft/submitted/reviewed → cancelled
```

Transitions validated server-side with permission checks (manager group required for approve/reject).

## Security
Groups reused from amnus_core: `group_amnus_user`, `group_amnus_manager`, `group_amnus_admin`.

ACLs in `security/ir.model.access.csv` (using `amnus_core.` prefix for groups).

Record rules in `security/security.xml` (company isolation).

## Views
- `crm.lead` form inherited (AMNUS tab with implementation fields)
- `crm.lead` search inherited (AMNUS implementation filter, request type group-by)
- `amnus.crm.project.request` list/form/search views
- AMNUS CRM menu under AMNUS root

## Tests
- `tests/test_installation.py` — module installed, lead extension, request model
- `tests/test_crm_lead.py` — implementation flag, request type, date validation, estimated users, tags, normal lead
- `tests/test_project_request.py` — create, sequence, relationship, state transitions, invalid transitions, date validation, estimated users, company, audit
- `tests/test_security.py` — user/manager permissions, unauthorized approval, cross-company isolation

All tagged `at_install`. 23 tests, 0 failures, 0 errors.

## Dependencies
- amnus_core
- crm
- contacts
- mail

## Internationalization
- Translatable strings wrapped in `_()`.

## Installation
Install `amnus_crm` from the Odoo Apps list after `amnus_core` is installed.
