# System Architecture — AMNUS

## 1. Overview

AMNUS (Odoo Project Lifecycle Management Platform) is a modular enterprise platform built on
**Odoo 19 Community Edition**. It manages the complete lifecycle of Odoo implementation projects,
from customer acquisition to delivery, deployment, maintenance and support.

The architecture is **layered, modular, and dependency-controlled**. Each AMNUS addon is an
independent Odoo module with declared dependencies. `amnus_core` is the foundation; all other
addons depend on it directly or indirectly.

## 2. Target Environment (verified, read-only)

| Component | Detail |
|-----------|--------|
| Odoo edition/version | Odoo 19.0.0 Community (LGPL-3) |
| Odoo installation | `C:\Program Files\AmanusERP\odoo\` |
| Python (Odoo-bundled) | 3.12.10 at `C:\Program Files\AmanusERP\python\` |
| System Python | 3.14.4 at `C:\Program Files\Python314\` (at Odoo 19 MAX_PY_VERSION 3.14 boundary) |
| PostgreSQL | 16.14 at `C:\Program Files\AmanusERP\PostgreSQL16\` |
| PostgreSQL service | `AmanusERPPostgreSQL16` (Running) |
| Odoo config | `C:\Program Files\AmanusERP\config\` (dev.conf, production.conf, lowmem.conf) |
| addons_path | `odoo/addons,custom_addons` (relative to `C:\Program Files\AmanusERP\`) |
| Custom addons dir | `C:\Program Files\AmanusERP\custom_addons\` |
| Git repository | None exists yet (to be initialized for AMNUS) |

Odoo 19 requirements: Python 3.10–3.14, PostgreSQL ≥ 13. Environment is compatible.

## 3. Architectural Layers

### Layer 1 — Foundation (`amnus_core`)
Shared models, security base, constants, helpers, and cross-cutting concerns. No dependency on
other AMNUS addons. Depends only on Odoo Community modules (`base`, `mail`, `contacts`, etc.).

### Layer 2 — Domain Addons
Each owns a bounded context of the project lifecycle:
- `amnus_crm` — leads, opportunities, customer acquisition
- `amnus_projects` — projects, phases, deliverables
- `amnus_analysis` — requirements analysis, specifications
- `amnus_agile` — sprints, backlogs, ceremonies
- `amnus_development` — development tasks, version-control links
- `amnus_devops` — environments, CI/CD, deployment
- `amnus_qa` — testing, quality gates, UAT
- `amnus_timesheets` — time tracking, effort, cost
- `amnus_documents` — document management
- `amnus_support` — maintenance, support tickets, SLAs
- `amnus_dashboard` — KPIs, executive reporting

### Layer 3 — Presentation
Standard Odoo XML views (kanban, list, form, dashboard), OWL only when a rich client UI is
genuinely required.

### Layer 4 — Integration
Odoo ORM for data. Email via `mail`. Files via Odoo attachments. External integrations (Git, CI)
via dedicated models and services, never Enterprise-only connectors.

## 4. Reused Odoo Community Modules (verified present in `odoo/addons`)

`crm`, `project`, `account`, `stock`, `sale`, `purchase`, `hr`, `hr_timesheet`, `mail`, `contacts`,
`product`, `uom`, `analytic`, `board`, `web`, `website`, `website_project`, `survey`, `event`,
`maintenance`, `portal`, `payment`.

Not confirmed present in this build (verify before use): `documents`, `helpdesk`, `sign`.

## 5. Security Architecture

- Odoo record rules + access rights (`ir.model.access.csv`, `<module>_security.xml`).
- Security groups per functional area.
- Multi-company (`res.company`) aware where applicable.
- `sudo()` used only when justified and documented.
- No credentials in code; secrets via Odoo `ir.config_parameter` or environment variables.

## 6. Data & Integrity

- Odoo ORM preferred; direct SQL avoided unless justified and documented.
- All models inherit from `models.Model` (or `AbstractModel`/`TransientModel` for wizards).
- Constraints via Odoo constraints (`models.Constraint`, `_sql_constraints` where appropriate).
- External IDs prefixed with module name (`amnus_core_xxx`).

## 7. Internationalization & Accessibility

- All user-facing strings wrapped in `_()`.
- Translation files under `i18n/` (`fr_FR`, `ar_SA`).
- Arabic `ar_SA` requires RTL support in views/CSS; test RTL layout.
- Production config language: `fr_FR`.

## 8. Deployment & Operations

- Odoo server run via `odoo-bin -c <config>`.
- Config profiles: dev (`dev.conf`), production (`production.conf`), low-memory (`lowmem.conf`).
- `db_filter` restricts database access in production (`^amanus$`).
- Windows requires threaded mode (`workers = 0`).
- Filestore under `C:\ProgramData\AmanusERP\filestore` (production config).

## 9. Testing Strategy

- Unit/integration tests in `tests/` per addon.
- Run with `--test-enable`.
- Tags: `post_install`, `at_install`.
- CI pattern exists in sibling `amanus_restaurant_cafe/.github/workflows/ci.yml` (Odoo 19 +
  PostgreSQL via GitHub Actions).

## 10. Known Constraints & Risks

| Concern | Detail |
|---------|--------|
| Python version | System Python 3.14.4 sits at Odoo 19 MAX_PY_VERSION (3.14). Use the Odoo-bundled Python 3.12.10 for development/running. |
| Existing `amanus_*` ecosystem | `custom_addons` contains `amanus_base`, `amanus_support`, etc. Proposed prefix is `amnus_` (no `a`). No name conflict, but `amanus_support` vs `amnus_support` are close — avoid confusion. |
| `documents` module | Not seen in `odoo/addons` listing. Verify availability before `amnus_documents` depends on it. |
| No Git repo | Initialize a Git repository for AMNUS before Sprint 01. |

## 11. Decision Log

No ADRs yet. First ADR expected in Sprint 01 (choice of `amnus_core` shared models and dependency direction).
