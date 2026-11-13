# AMNUS CRM

CRM extension for the AMNUS Odoo Project Lifecycle Management Platform.

## Models

### crm.lead (inherited)
AMNUS-specific fields added to standard CRM leads/opportunities:
- `amnus_is_implementation` — whether this concerns an Odoo implementation
- `amnus_request_type` — new_implementation, customization, migration, integration, support, training, consulting, other
- `amnus_project_summary` — description of requested solution
- `amnus_current_system` — customer's current system
- `amnus_expected_start_date` / `amnus_expected_go_live` — implementation dates
- `amnus_estimated_users` — estimated number of users
- `amnus_company_size` — small/medium/large/enterprise
- `amnus_technical_notes` — internal technical notes
- `amnus_tag_ids` — Many2many to `amnus.tag`

### amnus.crm.project.request
Structured implementation request associated with a CRM opportunity:
- `name` — sequence-generated reference (AMNUS-CRM-YYYY-XXXX)
- `lead_id` — required Many2one to crm.lead
- `partner_id` / `contact_id` — related customer/contact
- `request_type` — Selection
- `description`, `scope_summary`, `notes` — Text fields
- `expected_start_date`, `expected_go_live` — Date fields
- `estimated_users` — Integer
- `state` — draft → submitted → reviewed → approved/rejected/cancelled
- `company_id`, `user_id` — company and responsible

## Workflow

```
draft → submitted → reviewed → approved
                            → rejected
draft/submitted/reviewed → cancelled
```

## Security Groups (reused from amnus_core)

| Group | Access |
|-------|--------|
| AMNUS User | Read, create, write requests; cannot unlink |
| AMNUS Manager | Full access + approve/reject |
| AMNUS Admin | Full access |

## Dependencies
- amnus_core
- crm
- contacts
- mail

## Tests

Run with:
```
odoo-bin -c <config> --test-enable -d <test_db> -i amnus_crm
```

Odoo 19 Community Edition only. No Enterprise dependencies.
No modifications to existing `amanus_*` modules.
