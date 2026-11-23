# Sprint 06 — Fit-Gap & Solution Design

## Objective

Implement the `amnus_fitgap` addon on Odoo 19 Community, providing structured
Fit-Gap assessment of approved requirements against standard Odoo capabilities.

## Scope

- Addon: `amnus_fitgap`
- Depends on: `amnus_core`, `amnus_analysis`
- Models: `amnus.fitgap.assessment`, `amnus.fitgap.assessment.version`
- Native Odoo 19 views, security groups, ACLs, record rules, translations.

## Key design

- Outcome (8 values) separate from workflow state (7 values).
- Five effort categories with computed total.
- Explicit `is_current` marker plus PostgreSQL partial unique index
  `UNIQUE(requirement_id) WHERE is_current = TRUE`.
- Replacement approval is atomic: previous current assessment is superseded and
  the new assessment promoted in one transaction.
- Approved assessments are immutable; revisions create a new candidate assessment.
- Immutable version snapshots created on approval.
- Evidence stored via `ir.attachment` Many2many.

## Security

- Groups: user, manager, admin with implication hierarchy.
- Multi-company and project visibility record rules.
- Attachment access relies on Odoo comodel access checks.

## Tests

- 41 tests in `amnus_fitgap` suite, all passing.
- Regression suites to be run sequentially.

## Deferred

- Controlled Odoo capability catalog.
- Customer portal acceptance.
- Agile integration.
