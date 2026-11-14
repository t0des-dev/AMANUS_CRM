# Addons Architecture — AMNUS

## 1. Naming Convention

All custom AMNUS addons use the technical prefix **`amnus_`**.

Planned addons:

| # | Addon | Bounded Context | Depends On | Status |
|---|-------|-----------------|------------|--------|
| 1 | amnus_core | Core foundation, shared models, security | Odoo Community (`base`) | Implemented (Sprint 01) |
| 2 | amnus_crm | Customer acquisition, leads, opportunities | amnus_core, `crm`, `mail` | Implemented (Sprint 02) |
| 3 | amnus_projects | Project lifecycle, phases, deliverables | amnus_core, amnus_crm, `project` (`sale` deferred) | Discovery (Sprint 03) |
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

To be defined in Sprint 01. Candidates:
- `amnus.project` (base project, inherited/extended by `amnus_projects`)
- `amnus.partner_role` (project roles)
- `amnus.category` / `amnus.tag` (classification)
- `amnus.metric` / `amnus.kpi` (dashboard metrics)
- `amnus.attachment` wrapper (document handling)
- `amnus.audit.log` (change tracking)

Other addons inherit or reference these via `Many2one`/`Many2many` fields; they do not redefine them.

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

No ADRs yet. First ADR expected in Sprint 01 (shared models in `amnus_core`, and whether
`amnus_documents` builds on Odoo `documents` or a custom model).
