# ADR-001 — AMNUS Core Module

## Status
Accepted — Sprint 01

## Context
AMNUS requires a shared foundation layer upon which all domain addons (CRM, Projects, Agile,
Development, DevOps, QA, Timesheets, Documents, Support, Dashboard) depend. Odoo 19 Community
provides `base`, `mail`, `contacts`, etc., but nothing AMNUS-specific.

## Decision
Create `amnus_core` as the single root addon of the AMNUS platform.

- Addon name: `amnus_core`
- Technical prefix: `amnus_` (distinct from the pre-existing `amanus_*`
  ecosystem under `C:\Program Files\AmanusERP\custom_addons\`)
- Version: `19.0.1.0.0`
- Depends: `base` only (Community)
- Application: True, Installable: True, Auto install: False

## Shared models introduced
- `amnus.tag` — reusable tags (name, color, active, category, description, company_id).
- `amnus.audit.log` — immutable shared audit event log.

## Configuration
Extends `res.config.settings` with `amnus_enabled` and `amnus_audit_logging`
stored in `ir.config_parameter`.

## Consequences
- All future AMNUS addons must declare `amnus_core` in `depends`.
- `amnus_core` depends on no other AMNUS addon (root of the dependency DAG).
- No Enterprise modules are used.
- Existing `amanus_*` modules are untouched.

## Related
ADR-002 (Security Model)
