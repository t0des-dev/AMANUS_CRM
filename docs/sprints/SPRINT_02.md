# SPRINT 02 — CRM & Customer Relationship Management

## Objective
Implement the AMNUS CRM addon (`amnus_crm`) on Odoo 19 Community Edition.

## Deliverables

### Files created
- `addons/amnus/amnus_crm/__init__.py`
- `addons/amnus/amnus_crm/__manifest__.py`
- `addons/amnus/amnus_crm/models/__init__.py`
- `addons/amnus/amnus_crm/models/crm_lead.py`
- `addons/amnus/amnus_crm/models/amnus_crm_project_request.py`
- `addons/amnus/amnus_crm/security/ir.model.access.csv`
- `addons/amnus/amnus_crm/security/security.xml`
- `addons/amnus/amnus_crm/data/ir_sequence_data.xml`
- `addons/amnus/amnus_crm/views/crm_lead_views.xml`
- `addons/amnus/amnus_crm/views/amnus_crm_project_request_views.xml`
- `addons/amnus/amnus_crm/views/amnus_menus.xml`
- `addons/amnus/amnus_crm/tests/__init__.py`
- `addons/amnus/amnus_crm/tests/test_installation.py`
- `addons/amnus/amnus_crm/tests/test_crm_lead.py`
- `addons/amnus/amnus_crm/tests/test_project_request.py`
- `addons/amnus/amnus_crm/tests/test_security.py`
- `addons/amnus/amnus_crm/static/description/index.html`
- `addons/amnus/amnus_crm/README.md`
- `docs/technical/amnus_crm.md`

### Files modified
- `CHANGELOG.md` — added Sprint 02 entry
- `README.md` — updated addon table

## Architecture decisions
- Reused `crm.lead` (not replaced) for leads/opportunities
- Created `amnus.crm.project.request` for structured implementation requests
- No `amnus.project` model (belongs to future `amnus_projects` addon)
- Security groups reused from `amnus_core`
- ACLs in CSV (groups already exist from `amnus_core`)
- Sequence for request references: `AMNUS-CRM-YYYY-XXXX`

## Models and fields
See `docs/technical/amnus_crm.md` for full model/field documentation.

## Security
- ACLs in `security/ir.model.access.csv` (using `amnus_core.` prefix for groups)
- Record rules in `security/security.xml` (company isolation)
- Workflow transitions validated server-side with permission checks
- Audit logging via `amnus.audit.log._log_event()` on submit/approve

## Automated tests
- 23 at_install tests, 0 failures, 0 errors
- Installation, CRM fields, project requests, security, cross-company isolation

## amnus_core regression
- 34 at_install tests, 0 failures, 0 errors

## Database
- `amnus_test_19` (PostgreSQL 16.14, dedicated test database)

## Git
- Branch: `feature/sprint-02-amnus-crm`
- Commit: (to be committed)

## Known limitations
- No Arabic translations yet (i18n files not created for amnus_crm)
- CRM lead search view inheritance uses `view_crm_case_opportunities_filter` (verify availability)
- `amnus_current_system` is Char, could be Selection in future
- No smart button on CRM lead for implementation requests yet (future enhancement)

## Readiness for Sprint 03
Ready. `amnus_core` and `amnus_crm` are both installed and validated.
Sprint 03 may begin implementation of the next domain addon.
