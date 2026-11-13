# AMNUS Core — Technical Documentation

## Overview
`amnus_core` is the foundation addon of the AMNUS platform. It provides shared
infrastructure (tags, audit log, configuration, menu, security) used by all future
AMNUS domain addons.

## Module manifest
- Name: AMNUS Core
- Version: 19.0.1.0.0
- Category: Services
- License: LGPL-3
- Depends: `base`
- Application: True
- Installable: True
- Auto install: False

## Models

### amnus.tag
| Field | Type | Attributes |
|-------|------|------------|
| name | Char | required, translate |
| color | Integer | — |
| active | Boolean | default True |
| category | Selection | general/project/analysis/agile/development/qa/support |
| description | Text | translate |
| company_id | Many2one (res.company) | default current company |

Constraint: `UNIQUE(name, category, company_id)`.

### amnus.audit.log
| Field | Type | Attributes |
|-------|------|------------|
| name | Char | required, readonly |
| date | Datetime | default now, readonly |
| user_id | Many2one (res.users) | readonly |
| model_name | Char | readonly |
| record_id | Integer | readonly |
| action | Selection | create/update/delete/state_change/login/export/other |
| description | Text | readonly |
| company_id | Many2one (res.company) | readonly |

`write()` and `unlink()` raise `AccessError` (append-only). Creation via
internal API `log_event()` using controlled `sudo()`.

## Configuration (`res.config.settings`)
- `amnus_enabled` → `ir.config_parameter` `amnus_core.enabled`
- `amnus_audit_logging` → `ir.config_parameter` `amnus_core.audit_logging`

## Security
Groups: `group_amnus_user`, `group_amnus_manager`, `group_amnus_admin`
(implication hierarchy User ← Manager ← Admin).

ACLs in `security/ir.model.access.csv`. Audit log access restricted to managers and
administrators; create/write/unlink denied except via internal API.

## Menu
```
AMNUS
├── Overview
├── Configuration
│   ├── Tags
│   └── Settings
└── Administration
    └── Audit Logs
```

## Tests
- `tests/test_amnus_tag.py` — create, required name, duplicates, archive, search.
- `tests/test_amnus_audit_log.py` — log_event API, immutability, user access restriction.
- `tests/test_security.py` — groups, hierarchy, ACLs, audit restriction.

## Dependencies
- Odoo 19 Community only.
- Depends on `base`.
- No Enterprise modules.
- Does not modify existing `amanus_*` modules.

## Installation
Install `amnus_core` from the Odoo Apps list after adding the addons path.
