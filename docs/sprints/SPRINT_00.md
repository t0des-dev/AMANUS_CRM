# SPRINT 00 — Discovery & Technical Foundation

## 1. Objective

Analyze the existing development environment and establish a clean, scalable, maintainable technical
architecture for AMNUS. **No business functionality implemented in this Sprint.**

## 2. Scope (In / Out)

In scope:
- Environment discovery (Odoo, Python, PostgreSQL, addons paths, config, Git).
- Architecture design (modular, dependency-controlled).
- Documentation (AGENTS.md, README, CHANGELOG, LICENSE, docs/).
- Dependency strategy and naming convention (`amnus_` prefix).

Out of scope:
- Implementing any `amnus_*` business addon.
- Modifying existing `amanus_*` / `business_starter_*` addons.
- Creating or modifying databases.
- Installing packages or altering system configuration without approval.

## 3. Environment Discovery (verified)

| Item | Value |
|------|-------|
| Odoo | 19.0.0 Community (LGPL-3) |
| Odoo path | `C:\Program Files\AmanusERP\odoo\` |
| Python (Odoo-bundled) | 3.12.10 |
| System Python | 3.14.4 |
| PostgreSQL | 16.14 (`C:\Program Files\AmanusERP\PostgreSQL16\`) |
| PG service | `AmanusERPPostgreSQL16` (Running) |
| Config dir | `C:\Program Files\AmanusERP\config\` |
| addons_path | `odoo/addons,custom_addons` |
| Custom addons dir | `C:\Program Files\AmanusERP\custom_addons\` |
| Git repo | None (to initialize) |

Compatible with Odoo 19 (Python 3.10–3.14, PG ≥ 13): **Yes.**

## 4. Deliverables Created

- `AGENTS.md` — permanent development rules
- `README.md` — project overview
- `CHANGELOG.md` — change log
- `LICENSE` — LGPL-3
- `docs/architecture/system_architecture.md`
- `docs/architecture/addons_architecture.md`
- `docs/architecture/dependency_matrix.md`
- `docs/technical/development_standards.md`
- `docs/technical/environment_setup.md`
- `docs/technical/security_standards.md`
- `docs/sprints/SPRINT_00.md`

## 5. Architecture Summary

- `amnus_core` foundation; 11 domain addons (`amnus_crm`, `amnus_projects`, ...).
- Prefix `amnus_` (no conflict with existing `amanus_*` ecosystem).
- Reuse Odoo Community modules: crm, project, account, stock, sale, hr_timesheet, mail, etc.
- `documents` module availability to verify before `amnus_documents`.

## 6. Unresolved Technical Questions

1. Initialize Git repository for AMNUS (recommended on `main`)?
2. `documents` module: confirm availability in this Odoo 19 build, or implement custom model?
3. How to expose AMNUS addons to Odoo for testing: symlink into `custom_addons/`, or add a local
   dev addons path? (approval required)
4. Confirm `amnus_core` shared model list (candidates: `amnus.project`, `amnus.kpi`,
   `amnus.audit.log`, `amnus.tag`).
5. Production database credentials: replace `CHANGE_ME_*` placeholders (per environment, approval).

## 7. Recommended Plan for Sprint 01

1. Initialize Git repo; create `main` branch; add `.gitignore`.
2. Implement `amnus_core` (manifest, security base, shared models, menu).
3. Add automated tests for `amnus_core`.
4. Verify `amnus_core` loads in Odoo 19 (manifest import, `--test-enable`).
5. Update `docs/architecture/` with first ADRs (shared models, dependency direction).
6. Update `CHANGELOG.md` and `AGENTS.md` if rules evolve.

## 8. Acceptance Criteria (Sprint 00)

- [x] Environment inspected (read-only).
- [x] Architecture documented.
- [x] Addon naming convention established (`amnus_`).
- [x] Dependency strategy documented.
- [x] `AGENTS.md` created.
- [x] No business functionality implemented prematurely.
- [x] No existing project files destroyed.
- [x] Documentation consistent.

## 9. Readiness for Sprint 01

**READY** — Environment verified, architecture documented, naming and dependency strategy defined,
AGENTS.md in place. Sprint 01 may begin implementation of `amnus_core` after Git initialization and
approval for the chosen addons-path exposure method.
