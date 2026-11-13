# Environment Setup — AMNUS

## 1. Verified Environment (read-only inspection)

| Component | Detail | Source |
|-----------|--------|--------|
| Odoo edition/version | Odoo 19.0.0 Community (LGPL-3) | `release.py` |
| Odoo installation | `C:\Program Files\AmanusERP\odoo\` | filesystem |
| Odoo server entry | `odoo-bin` | `odoo-bin` |
| Python (Odoo-bundled) | 3.12.10 | `C:\Program Files\AmanusERP\python\python.exe --version` |
| System Python | 3.14.4 | `C:\Program Files\Python314\python.exe --version` |
| PostgreSQL | 16.14 | `postgres.exe --version`, `psql.exe --version` |
| PostgreSQL install | `C:\Program Files\AmanusERP\PostgreSQL16\` | filesystem |
| PostgreSQL service | `AmanusERPPostgreSQL16` (Running) | services |
| Odoo config dir | `C:\Program Files\AmanusERP\config\` | filesystem |
| Config files | dev.conf, production.conf, lowmem.conf | filesystem |
| addons_path | `odoo/addons,custom_addons` | config files |
| Custom addons dir | `C:\Program Files\AmanusERP\custom_addons\` | filesystem |
| Filestore (prod) | `C:\ProgramData\AmanusERP\filestore` | production.conf |
| Git repository | None exists | filesystem |

Odoo 19 requires: Python 3.10–3.14, PostgreSQL ≥ 13. **Environment is compatible.**

> Note: System Python 3.14.4 is at the Odoo 19 MAX_PY_VERSION boundary (3.14). Use the Odoo-bundled
> Python 3.12.10 for running/developing against Odoo.

## 2. Odoo Configuration Profiles

### dev.conf (local development)
- `addons_path = odoo/addons,custom_addons`
- `db_host = localhost`, `db_port = 5432`
- `db_user = amanus`, `db_name = amanus`
- `http_port = 8069`, `dev_mode = reload`
- `workers = 0` (Windows threaded mode)
- Passwords are placeholders (`CHANGE_ME_*`) — do not reuse or commit.

### production.conf
- `addons_path = C:/Program Files/AmanusERP/odoo/addons,C:/Program Files/AmanusERP/custom_addons`
- `db_port = 55432`, `dbfilter = ^amanus$`, `language = fr_FR`
- `workers = 0`, `proxy_mode = True`
- `list_db = False`

### lowmem.conf
- For machines ≤ 4 GB RAM; lower memory limits.

> Credentials: do not copy passwords from config files into version control. Treat
> `CHANGE_ME_*` values as placeholders to be replaced per environment.

## 3. How to Run Odoo (read-only, no changes)

From the Odoo installation root (`C:\Program Files\AmanusERP\`):

```
C:\Program Files\AmanusERP\python\python.exe odoo\odoo-bin -c config\dev.conf
```

Do not restart services or modify production configuration without explicit approval.

## 4. Adding AMNUS Addons to Odoo (non-destructive)

AMNUS addons live in this repository under `addons/amnus/`. To make them discoverable by Odoo for
testing, choose one non-destructive option (approval required):

1. **Symlink** each `amnus_*` addon folder into `C:\Program Files\AmanusERP\custom_addons\` (keeps
   source in the repo; no copying).
2. **Add a dev addons path** to a local copy of `dev.conf` pointing at the repo's
   `addons/amnus/` directory (do not modify the shared production config).
3. **Copy** addons into `custom_addons/` only with explicit approval (not recommended during dev).

Never modify existing `amanus_*` or `business_starter_*` addons under `custom_addons/`.

## 5. Database

- Default database: `amanus` (dev/production config).
- Do not create, drop, or modify databases without explicit approval.
- Connect via PostgreSQL 16 on `localhost:5432` (dev) or `55432` (production).

## 6. Testing

- Run module tests: `odoo-bin -c config\dev.conf --test-enable --init=<module>`
- CI pattern reference: `amanus_restaurant_cafe/.github/workflows/ci.yml` (Odoo 19 + PostgreSQL
  via GitHub Actions).

## 7. Ports & Network

| Profile | HTTP Port | DB Port |
|---------|-----------|---------|
| dev | 8069 | 5432 |
| production | (per proxy) | 55432 |
