# AMNUS Core

Shared infrastructure for the AMNUS Odoo Project Lifecycle Management Platform.

## Models

| Model | Description |
|-------|-------------|
| `amnus.tag` | Reusable tags for classifying records across AMNUS modules. |
| `amnus.audit.log` | Shared audit log for important business operations. |

## Configuration

Extends `res.config.settings` with:
- **AMNUS Enabled** — enable/disable the AMNUS platform globally.
- **Audit Logging Enabled** — enable/disable audit logging.

## Security Groups

| Group | XML ID | Implies |
|-------|--------|---------|
| AMNUS User | `group_amnus_user` | — |
| AMNUS Manager | `group_amnus_manager` | AMNUS User |
| AMNUS Administrator | `group_amnus_admin` | AMNUS Manager |

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

Run with:
```
odoo-bin -c <config> --test-enable -d <test_db> -i amnus_core --test-tags=post_install
```

Odoo 19 Community Edition only. No Enterprise dependencies.
