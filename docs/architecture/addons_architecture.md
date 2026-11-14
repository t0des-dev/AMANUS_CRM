# Addons Architecture — AMNUS

## 1. Naming Convention

All custom AMNUS addons use the technical prefix **`amnus_`**.

Planned addons:

| # | Addon | Bounded Context | Depends On | Status |
|---|-------|-----------------|------------|--------|
| 1 | amnus_core | Core foundation, shared models, security | Odoo Community (`base`) | Implemented (Sprint 01) |
| 2 | amnus_crm | Customer acquisition, leads, opportunities | amnus_core, `crm`, `mail` | Implemented (Sprint 02) |
| 3 | amnus_projects | Project lifecycle, deliverables, CRM handover | amnus_core, amnus_crm, `project`, `mail` (`sale` deferred) | Implemented (Sprint 03) |
| 4 | amnus_analysis | Requirements analysis, specifications | amnus_core, amnus_projects |
| 5 | amnus_agile | Sprints, backlogs, ceremonies | amnus_core, amnus_projects |
| 6 | amnus_development | Development tasks, version-control links | amnus_core, amnus_projects, amnus_agile |
| 7 | amnus_devops | Environments, CI/CD, deployment | amnus_core, amnus_projects |
| 8 | amnus_qa | Testing, quality gates, UAT | amnus_core, amnus_projects |
| 9 | amnus_timesheets | Time tracking, effort, cost | amnus_core, `hr_timesheet`, `account` |
| 10 | amnus_documents | Document management | amnus_core (verify `documents` module availability) |
| 11 | amnus_support | Maintenance, support tickets, SLAs | amnus_core, `mail`, `maintenance` |
| 12 | amnus_dashboard | KPIs, executive reporting | amnus_core, `board`, `analytic` |

## 2. Dependency Direction

```
amnus_dashboard
amnus_support       amnus_documents
      \                 /
       \               /
amnus_devops   amnus_qa   amnus_timesheets   amnus_analysis
       \         /          \               /
        \       /            \             /
amnus_development   amnus_agile   amnus_projects
       \           \             /
        \           \           /
amnus_crm ---------------------
       \                       /
        \                     /
          amnus_core (base)
                |
          Odoo Community modules
```

- `amnus_core` is the single root. Nothing depends on a "higher" addon.
- Dependencies flow downward only (no cycles).
- Each addon declares Odoo Community dependencies explicitly.

## 3. Shared Models (in `amnus_core`)

Implemented in Sprint 01:

- `amnus.tag` — reusable classification used by all AMNUS addons
- `amnus.audit.log` — append-only audit trail of important business operations
- `res.config.settings` — AMNUS platform/audit toggles
- AMNUS root menu and the base security groups (User, Manager, Administrator)

Project lifecycle is **not** a shared `amnus_core` model: `amnus_projects` extends
standard Odoo Project (`project.project`, `project.task`, stages, states and health)
and adds only `amnus.project.deliverable` (see ADR-003). Other addons reference the
standard project models and the shared AMNUS tag/audit APIs; they do not redefine them.

## 4. Addon Skeleton (template, not yet created)

Each `amnus_*` addon:

```
amnus_<name>/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <model>.py
├── security/
│   ├── ir.model.access.csv
│   └── <module>_security.xml
├── views/
│   ├── <model>_views.xml
│   └── menu.xml
├── data/
│   └── *.xml
├── i18n/
│   ├── fr_FR.po
│   └── ar_SA.po
├── tests/
│   ├── __init__.py
│   └── test_<module>.py
├── controllers/   (if needed)
├── static/        (if OWL/web assets needed)
├── wizard/        (if needed)
├── report/        (if needed)
├── demo/          (optional)
└── README.md
```

## 5. Manifest Rules (per AGENTS.md)

- `depends` lists all Odoo Community + AMNUS dependencies.
- `license`: `LGPL-3`.
- `application`: `True` for top-level modules; `False` for helper libraries.
- `auto_install`: `False` unless required.
- `data` includes security, views, menu, and data files.

## 6. Naming Conflicts Check (verified)

Existing `custom_addons` uses prefix `amanus_` (e.g. `amanus_base`, `amanus_support`).
AMNUS uses prefix `amnus_` (no second `a`). **No exact name conflict.**

Close-name watch: `amanus_support` exists; proposed `amnus_support` is distinct but similar —
documented to prevent confusion.

No existing addon uses the `amnus_` prefix.

## 7. Versioning

Odoo 19 pattern: `19.0.<major>.<minor>.<patch>`. Initial: `19.0.1.0.0`.

## 8. Decision Log

- ADR-001 — Core Module (`docs/architecture/ADRs/ADR-001-core-module.md`)
- ADR-002 — AMNUS Security Model (`docs/architecture/ADRs/ADR-002-security-model.md`)
- ADR-003 — Project Lifecycle Reuse and Deliverable Sign-off
  (`docs/architecture/ADRs/ADR-003-project-lifecycle-and-deliverables.md`)

Sprint 01 decisions: shared models live in `amnus_core`; naming, security and
versioning follow AGENTS.md. Sprint 03 decision: reuse standard Odoo Project and
keep only `amnus.project.deliverable` as a new business model.
