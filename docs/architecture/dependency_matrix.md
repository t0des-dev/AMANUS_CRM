# Dependency Matrix — AMNUS

## 1. AMNUS Internal Dependency Matrix

| Addon | amnus_core | amnus_crm | amnus_projects | amnus_analysis | amnus_agile | amnus_development | amnus_devops | amnus_qa | amnus_timesheets | amnus_documents | amnus_support | amnus_dashboard |
|-------|-----------:|----------:|---------------:|---------------:|------------:|------------------:|-------------:|---------:|-----------------:|----------------:|--------------:|----------------:|
| amnus_core | — | | | | | | | | | | | |
| amnus_crm | ✓ | — | | | | | | | | | | |
| amnus_projects | ✓ | ✓ | — | | | | | | | | | |
| amnus_analysis | ✓ | | ✓ | — | | | | | | | | |
| amnus_agile | ✓ | | ✓ | | — | | | | | | | |
| amnus_development | ✓ | | ✓ | | ✓ | — | | | | | | |
| amnus_devops | ✓ | | ✓ | | | | — | | | | | |
| amnus_qa | ✓ | | ✓ | | | | | — | | | | |
| amnus_timesheets | ✓ | | | | | | | | — | | | |
| amnus_documents | ✓ | | | | | | | | | — | | |
| amnus_support | ✓ | | | | | | | | | | — | |
| amnus_dashboard | ✓ | | | | | | | | | | | — |

✓ = depends on. Blank = no dependency. `—` = self.

## 2. AMNUS → Odoo Community Dependencies (verified present)

| AMNUS Addon | Odoo Community Modules (in `odoo/addons`) | Status |
|-------------|-------------------------------------------|--------|
| amnus_core | base | ✓ Verified — Implemented (Sprint 01) |
| amnus_crm | crm, mail, contacts | ✓ Verified — Implemented (Sprint 02) |
| amnus_projects | project | ✓ Verified — Discovery (Sprint 03); `sale` intentionally deferred |
| amnus_analysis | project | ✓ Verified |
| amnus_agile | project | ✓ Verified |
| amnus_development | project | ✓ Verified |
| amnus_devops | project | ✓ Verified |
| amnus_qa | project | ✓ Verified |
| amnus_timesheets | hr_timesheet, account | ✓ Verified |
| amnus_documents | documents *(verify)* | ⚠ Verify availability |
| amnus_support | mail, maintenance | ✓ Verified |
| amnus_dashboard | board, analytic | ✓ Verified |

`crm`, `project`, `account`, `stock`, `sale`, `hr_timesheet`, `mail`, `contacts`, `product`, `uom`,
`analytic`, `board`, `web`, `maintenance` are all present in `C:\Program Files\AmanusERP\odoo\addons`.

## 3. Odoo Community Modules NOT Confirmed (verify before use)

| Module | Reason |
|--------|--------|
| documents | Not seen in `odoo/addons` listing; `amnus_documents` may need a custom model |
| helpdesk | Not present; `amnus_support` should use `mail` + custom ticket model, or verify |

Never assume Enterprise-only modules are available (e.g. no `helpdesk` Enterprise features, no
`sign`, no `studio`).

## 4. Existing `custom_addons` Ecosystem (`amanus_*` prefix)

| Addon | Version | Depends On | Notes |
|-------|---------|------------|-------|
| amanus_base | 19.0.1.0.6 | product, stock, product_expiry | Amanus ERP foundation |
| amanus_support | 19.0.1.1.0 | base, bus, amanus_base, point_of_sale | Support/license/audit |

Note: existing prefix is `amanus_`; AMNUS uses `amnus_`. No conflict, but names are similar
(e.g. `amanus_support` vs `amnus_support`).

## 5. Dependency Rules

- No circular dependencies between AMNUS addons.
- `amnus_core` depends on no other AMNUS addon.
- Declare Community dependencies in `__manifest__.py` `depends`.
- Prefer Community Edition only; never Enterprise.
- `depends_optional` only for optional integrations.
