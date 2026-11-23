# AMNUS Fit-Gap

Fit-Gap & Solution Design addon for the AMNUS Odoo Project Lifecycle Management Platform.

## Overview

`amnus_fitgap` provides structured assessment of approved business requirements against
the standard capabilities of Odoo 19 Community Edition. Each assessment records the
implementation outcome, standard Odoo capability reference, gap analysis, proposed
solution, effort estimation and risk.

## Dependencies

- `amnus_core`
- `amnus_analysis`

## Models

- `amnus.fitgap.assessment` — Fit-Gap assessment with controlled lifecycle.
- `amnus.fitgap.assessment.version` — Immutable snapshot of an approved assessment.

## License

LGPL-3
