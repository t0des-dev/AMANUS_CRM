# AMNUS — AGENTS.md

Permanent development rules for the AMNUS — Odoo Project Lifecycle Management Platform.
These rules apply to every agent, contributor, and sprint. They are non-negotiable and must be
followed for all AMNUS work targeting Odoo 19 Community Edition.

---

## 1. Target Platform

- **Always target Odoo 19 Community Edition.** Never target Odoo Enterprise.
- Odoo installation: `C:\Program Files\AmanusERP\odoo\` (Odoo 19.0.0, LGPL-3).
- Bundled Python interpreter: `C:\Program Files\AmanusERP\python\` (Python 3.12.10).
- PostgreSQL: `C:\Program Files\AmanusERP\PostgreSQL16\` (PostgreSQL 16.14).
- Do not assume a component is installed without verification. Report unknowns as UNKNOWN.

## 2. Odoo Development Conventions

- Follow official Odoo 19 development conventions (model naming, view architecture, manifest keys).
- Use the Odoo ORM (`self.env`, `search`, `create`, `write`, `unlink`) instead of direct SQL unless
  a performance or reporting requirement is documented and justified.
- Never modify Odoo core files under `C:\Program Files\AmanusERP\odoo\odoo\` or `odoo/addons/`.
- Never introduce Enterprise-only dependencies or modules (`enterprise` folder, `.enterprise` manifests).
- Respect existing module dependencies; declare them explicitly in `__manifest__.py`.

## 3. Module Naming & Manifest

- All custom AMNUS addons use the technical prefix: **`amnus_`** (e.g. `amnus_core`, `amnus_crm`).
- Each addon must have a valid `__manifest__.py` with: `name`, `version`, `category`, `summary`,
  `author`, `website`, `license`, `depends`, `data`, `installable`, `application`.
- Use Odoo 19 version pattern: `19.0.1.0.0`.
- License: LGPL-3 (matching Odoo Community).
- Set `auto_install: False` unless explicitly required.

## 4. Python Coding Standards

- Follow PEP 8. Use 4-space indentation, double quotes for strings where consistent with the file.
- Type hints are encouraged for new models and methods.
- Docstrings on public methods and models.
- No bare `except`. Log exceptions via `odoo.tools` logging or `_logger`.
- Avoid importing Odoo internals that are private (underscore-prefixed).
- Keep model classes small and cohesive; one business object per model where practical.

## 5. XML Views & Data

- Declare all data files in `__manifest__.py` under `data` (and `demo` for demonstration data).
- Use external IDs (`xml_id`) consistently; prefix them with the module name (e.g. `amnus_project_view_form`).
- Menu items and actions must be declared in XML under `data`.
- Do not hardcode database IDs in XML data files.

## 6. Security

- Implement security access rights via `security/ir.model.access.csv` for every model.
- Implement record rules via `security/<module>_security.xml` where row-level access control is required.
- Define security groups in `security/<module>_groups.xml` and assign them in access CSV.
- Use `sudo()` only when justified and documented; never to bypass security silently.
- No credentials, API keys, or secrets in source code or documentation. Use environment variables or
  Odoo system parameters (ir.config_parameter) for secrets.
- OWASP / Odoo security best practices apply to controllers and website-facing endpoints.

## 7. No Duplicated Functionality

- Before creating a model or feature, check whether an existing Odoo Community module or an existing
  `amanus_*`/`amnus_*` module already provides it.
- Reuse standard Community modules: `crm`, `project`, `account`, `stock`, `sale`, `hr_timesheet`,
  `mail`, `contacts`, `product`, `uom`, `analytic`, `board`, `web`.
- Extend rather than duplicate. Inherit (`_inherit`) existing models instead of redefining them.

## 8. Dependency Management

- Declare all dependencies in `__manifest__.py` `depends`.
- Prefer Community Edition modules only. Never assume Enterprise modules are available.
- Controlled dependencies between AMNUS addons: `amnus_core` is the foundation; other addons depend
  on it and on Community modules as needed. Avoid circular dependencies.

## 9. Testing

- Add automated tests for business logic in every sprint (`tests/` directory per module).
- Tests must run under `--test-enable` with Odoo's test framework.
- Test tags: `post_install`, `at_install` where appropriate.
- Do not skip tests to "speed up" delivery.

## 10. Backward Compatibility

- Preserve backward compatibility within a major Odoo version (19.0.x).
- Do not remove database columns or models without a migration plan and deprecation notice.
- Data migration scripts (pre/post init hooks, `_auto_init`) must be idempotent.

## 11. Documentation

- Document every important architectural decision (Architecture Decision Records in `docs/architecture/`).
- Keep `docs/sprints/SPRINT_NN.md` up to date for each sprint.
- Update `CHANGELOG.md` on every change.
- Update AGENTS.md when rules evolve.

## 12. Git & Version Control

- Use Git for version control. Commit early, commit often.
- Meaningful commit messages: type(scope): subject (e.g. `feat(amnus_core): add project model`).
- Feature branches off `main`; pull-request style review before merge.
- Do not commit secrets, `.pyc`, `__pycache__`, or build artifacts (see `.gitignore`).
- No force-push on shared branches.

## 13. Internationalization (i18n) & Arabic RTL

- All user-facing strings must be wrapped in `_()` for translation.
- Provide `.po` translation files under `i18n/` for at least `fr_FR` and `ar_SA`.
- Arabic (ar_SA) requires RTL support in OWL views and CSS; test RTL layout.
- Do not hardcode French or Arabic text in Python logic.

## 14. OWL (when required)

- Use OWL only when a rich client-side UI is genuinely required; prefer standard Odoo XML views.
- OWL components must follow Odoo 19 OWL standards and be registered in the module manifest assets.

## 15. Verification & Approval

- Verify every change before considering a task complete (import test, manifest load, unit tests).
- Do not install packages, alter system configuration, or modify databases without first explaining
  the proposed change and obtaining explicit approval.
- No destructive operations (`DROP DATABASE`, `unlink` of core data, dropping tables) without explicit
  written approval.
- Never restart services or change production configuration without approval.

## 16. Non-Destructive Principle

- Never modify or delete existing custom addons (`amanus_*`, `business_starter_*`) under
  `C:\Program Files\AmanusERP\custom_addons\`.
- Never drop or modify existing databases.
- AMNUS addons are developed in this repository under `addons/amnus/` and linked into the Odoo
  `addons_path` for testing only with approval.

---

**If a rule is unclear, stop and ask before proceeding.**
