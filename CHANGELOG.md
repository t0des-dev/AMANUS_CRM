# Changelog — AMNUS

## Version 19.0.2.0.0 — Sprint 02 (CRM & Customer Relationship Management)

### Added
- `addons/amnus/amnus_crm` addon (implemented)
  - Manifest: name "AMNUS CRM", version 19.0.1.0.0, depends `amnus_core`, `crm`, `contacts`, `mail`, LGPL-3
  - `crm.lead` extension: AMNUS implementation flag, request type, project summary, current system, expected dates, estimated users, company size, technical notes, AMNUS tags
  - Model `amnus.crm.project.request`: structured implementation request with controlled workflow
  - Sequence: `AMNUS-CRM-YYYY-XXXX` for request references
  - Security: ACLs (CSV) + company isolation record rules
  - Views: CRM lead form/search inheritance, request list/form/search, AMNUS CRM menu
  - Automated tests: 23 at_install tests (installation, lead fields, project requests, security)
  - README, static description
- Documentation: `docs/technical/amnus_crm.md`, `docs/sprints/SPRINT_02.md`

### Changed
- README.md: `amnus_crm` status updated to implemented
- CHANGELOG.md: Sprint 02 entry added

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running
- Test database: `amnus_test_19`

### Runtime validation
- `amnus_crm` installed on `amnus_test_19`: state = installed
- Python compile: OK
- XML validation: OK (all files well-formed)
- Manifest validation: OK
- Automated tests: 23 at_install tests, 0 failures, 0 errors
- `amnus_core` regression: 34 at_install tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules untouched

## Version 19.0.1.1.0 — Sprint 01.1 (Core Runtime Validation & Security Hardening)

### Changed
- Manifest: added `base_setup` dependency (required for settings view inheritance)
- `amnus.tag`: replaced `_sql_constraints` with `models.Constraint` (Odoo 19 convention)
- `amnus.tag`: NULL-safe uniqueness constraint (global tags + company-specific tags)
- `amnus.audit.log`: renamed `log_event()` → `_log_event()` (non-RPC-callable)
- `amnus.audit.log`: identity (user/company) now derived from environment (not forgeable)
- `amnus.tag` and `amnus.audit.log`: added company isolation record rules
- `security.xml`: reorganized (groups before ACLs), removed `category_id` (not available in Odoo 19 `res.groups`)
- ACLs moved from CSV to XML for proper load ordering
- Views: `<tree>` → `<list>` (Odoo 19 view type name)
- Views: settings xpath updated to Odoo 19 pattern (`//form` with `<app>`/`<block>`/`<setting>`)
- `amnus_menus.xml`: `target="inline"` → `target="new"` (valid Odoo 19 value)
- Tests: expanded with global/company uniqueness, cross-company access, audit API protection, config persistence, menu visibility, security group inheritance
- Tests: `groups_id` → `group_ids` (Odoo 19 field name), `tree` → `list`
- i18n: added `amnus_core.pot`, `fr_FR.po`, `ar_SA.po`

### Fixed
- `_sql_constraints` no longer supported in Odoo 19 → `models.Constraint`
- `base_setup` dependency missing → added
- `category_id` field not on `res.groups` in Odoo 19 → removed
- `ir.model.access.csv` processed before groups defined → moved ACLs to XML
- `log_event()` RPC-callable → renamed to `_log_event()`
- Tag uniqueness not NULL-safe → added ORM constraint
- No record rules for multi-company → added company isolation rules
- `tree` view type invalid in Odoo 19 → changed to `list`

### Runtime validation
- Database: `amnus_test_19` created (PostgreSQL 16.14, owned by `amanus`, UTF8)
- Module installed: `amnus_core` state = installed
- Tests: 34 at_install tests, 0 failures, 0 errors
- All Python files compile, all XML files valid

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running

## Version 19.0.1.0.0 — Sprint 01 (Core Foundation)

### Added
- `addons/amnus/amnus_core` addon (implemented)
  - Manifest: name "AMNUS Core", version 19.0.1.0.0, depends `base`, LGPL-3
  - Model `amnus.tag` (reusable tags): name, color, active, category, description, company_id
  - Model `amnus.audit.log` (immutable audit log): name, date, user_id, model_name, record_id, action, description, company_id
  - `res.config.settings` extension: AMNUS Enabled, Audit Logging Enabled
  - Security groups: AMNUS User, AMNUS Manager, AMNUS Administrator (implication hierarchy)
  - ACLs in `security/ir.model.access.csv`
  - Menus and views: tags list/form/search, audit logs list/form/search, settings, AMNUS root menu
  - Automated tests: test_amnus_tag, test_amnus_audit_log, test_security
  - Static description, README
- `config/amnus-dev.conf.example` (development configuration sample)
- Documentation: ADR-001, ADR-002, docs/technical/amnus_core.md, docs/sprints/SPRINT_01.md

### Changed
- README.md, CHANGELOG.md, dependency matrix, addons architecture updated to reflect `amnus_core` implementation

### Environment (unchanged, verified)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running

### Notes
- `amnus_core` not yet installed against a database (pending dedicated test database approval).
- No existing `amanus_*` module or database was modified.

## Version 19.0.0.0.0 — Sprint 00 (Foundation & Documentation)

### Added
- Repository structure (AGENTS.md, README.md, CHANGELOG.md, LICENSE, docs/, config/, requirements/, scripts/, tests/)
- `addons/amnus/` container for future `amnus_*` addons (empty — no business modules yet)
- `docs/architecture/system_architecture.md`
- `docs/architecture/addons_architecture.md`
- `docs/architecture/dependency_matrix.md`
- `docs/technical/development_standards.md`
- `docs/technical/environment_setup.md`
- `docs/technical/security_standards.md`
- `docs/sprints/SPRINT_00.md`
- `AGENTS.md` with permanent development rules

### Environment discovered & verified (read-only)
- Odoo 19.0.0 Community at `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled); system Python 3.14.4
- PostgreSQL 16.14, service `AmanusERPPostgreSQL16` running
- Existing `custom_addons` ecosystem (`amanus_*` prefix) — no `amnus_` naming conflict
- No existing Git repository; one to be initialized for AMNUS

### Changed
- None

### Removed
- None

### Notes
- No business functionality implemented in this Sprint.
- No existing database, configuration, or custom addon was modified.
