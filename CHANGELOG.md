# Changelog — AMNUS

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
