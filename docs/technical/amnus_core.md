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
- Depends: `base`, `base_setup`
- Application: True
- Installable: True
- Auto install: False

`base_setup` is required because the settings view inherits
`base_setup.res_config_settings_view_form`.

## Models

### amnus.tag
| Field | Type | Attributes |
|-------|------|------------|
| name | Char | required, translate |
| color | Integer | — |
| active | Boolean | default True |
| category | Selection | general/project/analysis/agile/development/qa/support |
| description | Text | translate |
| company_id | Many2one (res.company) | default current company; empty = global tag |

Uniqueness policy (NULL-safe):
- Global tag (company_id empty): name+category unique among all global tags.
- Company-specific tag: name+category unique within that company.
- Same name in different categories: allowed.
- Same name in different companies: allowed (company isolation).
- Global tag and company-specific tag may share name+category (distinct scopes).

Enforced by a PostgreSQL `UNIQUE(name, category, company_id)` constraint plus a
NULL-aware ORM constraint (PostgreSQL treats NULL as distinct, so SQL alone does
not block duplicate global tags).

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

Append-only: `write()` and `unlink()` raise `AccessError`.
Creation via internal API `_log_event()` using scoped `sudo()`.
Identity (user/company) is derived from the authenticated environment — never from
caller arguments — so it cannot be forged.
`_log_event()` is underscore-prefixed and therefore not callable through Odoo's
XML-RPC / JSON-RPC interface.

## Configuration (`res.config.settings`)
- `amnus_enabled` → `ir.config_parameter` `amnus_core.enabled`
- `amnus_audit_logging` → `ir.config_parameter` `amnus_core.audit_logging`

## Security
Groups: `group_amnus_user`, `group_amnus_manager`, `group_amnus_admin`
(implication hierarchy User ← Manager ← Admin).

ACLs in `security/ir.model.access.csv`. Row-level company isolation via record rules
in `security/amnus_security.xml`:
- Tags: visible where company is global (NULL) or in the user's allowed companies.
- Audit logs: readable by managers/administrators, limited to global + their companies.
- Audit log create/write/unlink denied to all groups (enforced by ACL + ORM).

## Menu
```
AMNUS
├── Overview
├── Configuration (Manager+)
│   ├── Tags (User+)
│   └── Settings (Admin+)
└── Administration (Manager+)
    └── Audit Logs (Manager+)
```

## Tests
- `tests/test_amnus_tag.py` — create, required name, duplicates (global/company),
  same name different category/company, archive, search, update uniqueness.
- `tests/test_amnus_audit_log.py` — non-RPC exposure, internal API, identity
  integrity, company from environment, immutability, access restrictions.
- `tests/test_security.py` — groups, hierarchy, ACLs, tag access, audit access,
  menu visibility/restrictions, cross-company tag access.
- `tests/test_config.py` — settings persistence, defaults, toggle.

All tagged `amnus_core`, `post_install`.

## Dependencies
- Odoo 19 Community only.
- Depends on `base`, `base_setup`.
- No Enterprise modules.
- Does not modify existing `amanus_*` modules.

## Internationalization
- Translatable strings wrapped in `_()`.
- `i18n/amnus_core.pot` (template), `i18n/fr_FR.po`, `i18n/ar_SA.po`.
- Arabic (ar_SA) translations pending native review; RTL untested in the Odoo client.

## Installation
Install `amnus_core` from the Odoo Apps list after adding the addons path.
