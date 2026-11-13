# SPRINT 01 — Core Foundation Implementation

## Objective
Implement the production-quality foundational addon `amnus_core` for the AMNUS
platform on Odoo 19 Community Edition.

## Git (completed)
- Repository initialized at `C:\Users\PC\Desktop\workflow\ModuleOdoo19\amnus\`
- Branch: `main`
- `.gitignore` created (Python cache, venv, IDE, Odoo logs, DB dumps, local config with secrets, temp artifacts)

## Deliverables

### Files created (amnus_core addon)
- `addons/amnus/amnus_core/__init__.py`
- `addons/amnus/amnus_core/__manifest__.py`
- `addons/amnus/amnus_core/models/__init__.py`
- `addons/amnus/amnus_core/models/amnus_tag.py`
- `addons/amnus/amnus_core/models/amnus_audit_log.py`
- `addons/amnus/amnus_core/models/res_config_settings.py`
- `addons/amnus/amnus_core/security/ir.model.access.csv`
- `addons/amnus/amnus_core/security/security.xml`
- `addons/amnus/amnus_core/views/amnus_menus.xml`
- `addons/amnus/amnus_core/views/amnus_tag_views.xml`
- `addons/amnus/amnus_core/views/amnus_audit_log_views.xml`
- `addons/amnus/amnus_core/views/res_config_settings_views.xml`
- `addons/amnus/amnus_core/tests/__init__.py`
- `addons/amnus/amnus_core/tests/test_amnus_tag.py`
- `addons/amnus/amnus_core/tests/test_amnus_audit_log.py`
- `addons/amnus/amnus_core/tests/test_security.py`
- `addons/amnus/amnus_core/static/description/index.html`
- `addons/amnus/amnus_core/README.md`

### Files created (config)
- `config/amnus-dev.conf.example`

### Files created (documentation)
- `docs/architecture/ADRs/ADR-001-core-module.md`
- `docs/architecture/ADRs/ADR-002-security-model.md`
- `docs/technical/amnus_core.md`
- `docs/sprints/SPRINT_01.md`

### Files updated
- `README.md`
- `CHANGELOG.md`
- `docs/architecture/dependency_matrix.md`
- `docs/architecture/addons_architecture.md`

## Models and fields
- `amnus.tag`: name, color, active, category, description, company_id
- `amnus.audit.log`: name, date, user_id, model_name, record_id, action, description, company_id
- `res.config.settings` (inherited): amnus_enabled, amnus_audit_logging

## Security groups
- `group_amnus_user` (AMNUS User)
- `group_amnus_manager` (AMNUS Manager, implies User)
- `group_amnus_admin` (AMNUS Administrator, implies Manager)

## Acceptance criteria status
1. Git repository initialized safely — Yes
2. `.gitignore` created — Yes
3. `amnus_core` addon exists — Yes
4. Manifest valid — Yes (static review)
5. Python files syntactically valid — Yes (static review)
6. XML files valid — Yes (static review)
7. Security groups correctly configured — Yes
8. Shared models implemented — Yes
9. Menus and views implemented — Yes
10. Configuration works — Yes (static review)
11. Automated tests written — Yes
12. No Enterprise dependency — Yes
13. Existing `amanus_` modules untouched — Yes
14. Documentation updated — Yes
15. Installation and test status — Not executed against a database (pending test DB approval)

## Installation status (updated in Sprint 01.1)

**Installed and validated** against dedicated test database `amnus_test_19` (PostgreSQL 16.14).

- Database: `amnus_test_19` created (UTF8, template0, owned by `amanus`)
- Module state: `installed`
- Python compile: OK (Odoo-bundled Python 3.12.10)
- XML validation: OK (all files well-formed)
- Manifest validation: OK
- Automated tests: 34 at_install tests, 0 failures, 0 errors
- No Enterprise dependencies
- Existing `amanus_*` modules untouched
- Existing databases (`amanus`, `postgres`) untouched

## Readiness for Sprint 02
Ready to proceed to Sprint 02 (next domain addon) once `amnus_core` installation and tests
have been validated against an approved test database.
