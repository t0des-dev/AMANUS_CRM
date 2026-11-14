# AMNUS — Odoo Project Lifecycle Management Platform

AMNUS is a modular enterprise platform for managing the complete lifecycle of Odoo implementation
projects, from customer acquisition and requirements analysis to development, testing, delivery,
deployment, maintenance and support.

Built on **Odoo 19 Community Edition**, Python, PostgreSQL, and the Odoo ORM.

## Repository Structure

```text
amnus/
├── AGENTS.md              # Permanent development rules (read first)
├── README.md              # This file
├── CHANGELOG.md           # Change log
├── LICENSE                # LGPL-3
├── requirements/          # Python requirements
├── config/                # Odoo configuration samples
├── addons/                # Custom addons
│   └── amnus/
│       ├── amnus_core/
│       ├── amnus_crm/
│       ├── amnus_projects/
│       ├── amnus_analysis/
│       ├── amnus_agile/
│       ├── amnus_development/
│       ├── amnus_devops/
│       ├── amnus_qa/
│       ├── amnus_timesheets/
│       ├── amnus_documents/
│       ├── amnus_support/
│       └── amnus_dashboard/
├── docs/
│   ├── architecture/
│   ├── business_requirements/
│   ├── technical/
│   ├── security/
│   └── sprints/
├── scripts/
└── tests/
```

## Addons (naming prefix: `amnus_`)

| Addon | Status | Responsibility |
|-------|--------|----------------|
| amnus_core | **Implemented (Sprint 01)** | Core foundation, shared models, security base |
| amnus_crm | **Implemented (Sprint 02)** | CRM & customer relationship management |
| amnus_projects | **Implemented (Sprint 03)** | Project lifecycle, CRM handover, deliverables |
| amnus_analysis | Planned | Requirements analysis, specs, functional analysis |
| amnus_agile | Planned | Agile ceremonies, sprints, backlogs |
| amnus_development | Planned | Development tracking, tasks, version control links |
| amnus_devops | Planned | CI/CD, environments, deployment pipelines |
| amnus_qa | Planned | Testing, quality gates, UAT |
| amnus_timesheets | Planned | Time tracking, effort, cost |
| amnus_documents | Planned | Document management, specs, contracts |
| amnus_support | Planned | Maintenance, support tickets, SLAs |
| amnus_dashboard | Planned | Executive dashboards, KPIs, reporting |

`amnus_core`, `amnus_crm` and `amnus_projects` are installed and functional. The remaining addons are planned for future sprints.

## Environment (verified, Sprint 00)

- Odoo 19.0.0 Community — `C:\Program Files\AmanusERP\odoo\`
- Python 3.12.10 (Odoo-bundled) — `C:\Program Files\AmanusERP\python\`
- PostgreSQL 16.14 — `C:\Program Files\AmanusERP\PostgreSQL16\`
- Config samples — `C:\Program Files\AmanusERP\config\` (dev.conf, production.conf, lowmem.conf)

See `docs/technical/environment_setup.md` and `docs/architecture/dependency_matrix.md`.

## Getting Started

1. Read `AGENTS.md` — it contains the permanent rules.
2. Read `docs/architecture/system_architecture.md`.
3. Read `docs/technical/environment_setup.md`.
4. `amnus_core`, `amnus_crm` and `amnus_projects` are implemented; Sprint 04 begins the next domain addon.

## License

LGPL-3 (GNU Lesser General Public License v3). See `LICENSE`.
