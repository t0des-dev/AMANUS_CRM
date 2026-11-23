# AMNUS Fit-Gap Technical Documentation

## Models

### `amnus.fitgap.assessment`

Fit-Gap assessment linked to an approved requirement.

Key fields:
- Identity: `reference` (FG-00001), `name`, `requirement_id`
- Derived: `project_id`, `customer_id`, `company_id`
- Outcome: `outcome` (8 values)
- Capability reference: `standard_odoo_module`, `standard_odoo_feature`, `standard_behavior_description`
- Gap analysis: `gap_description`, `root_cause`, `business_impact`, `technical_impact`
- Implementation: `configuration_approach`, `development_approach`, `integration_approach`,
  `workaround_description`, `proposed_solution`, `technical_notes`, `dependencies`, `assumptions`
- Effort: five effort fields + computed `total_effort`
- Risk: `estimation_confidence`, `risk_level`
- Approval metadata: `approved_by`, `approved_date`, `rejected_by`, `rejected_date`, `rejection_reason`
- Evidence: `evidence_ids` (Many2many to `ir.attachment`)
- Lifecycle: `state` (7 values), `is_current`

### `amnus.fitgap.assessment.version`

Immutable snapshot created on approval. Write and unlink are rejected.

## Database constraint

Partial unique index:

```sql
CREATE UNIQUE INDEX amnus_fitgap_assessment_current_unique
ON amnus_fitgap_assessment (requirement_id)
WHERE is_current = TRUE;
```

## Workflow

draft -> in_analysis -> under_review -> approved/rejected/cancelled
approved -> superseded (via replacement approval)
revision creates a new non-current candidate assessment.
