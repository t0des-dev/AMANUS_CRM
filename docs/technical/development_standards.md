# Development Standards — AMNUS

## 1. General Rules (see AGENTS.md)

- Target Odoo 19 Community only.
- Follow official Odoo development conventions.
- Use the Odoo ORM; avoid direct SQL unless justified.
- Never modify Odoo core.
- Never introduce Enterprise dependencies.
- All custom addons use the `amnus_` prefix.

## 2. Python Standards

- PEP 8, 4-space indentation.
- Type hints on new models and public methods.
- Docstrings on public methods and models.
- No bare `except`; log via `_logger`.
- Do not import private Odoo internals (underscore-prefixed).
- One business object per model where practical.

## 3. Manifest (`__manifest__.py`)

Required keys:
- `name`, `version` (`19.0.x.y.z`), `category`, `summary`, `author`, `website`, `license` (`LGPL-3`)
- `depends` (all Odoo Community + AMNUS deps)
- `data` (security, views, menu, data)
- `installable: True`, `application: <bool>`
- `auto_install: False` unless required

Example:

```python
{
    "name": "AMNUS Core",
    "version": "19.0.1.0.0",
    "category": "Project Lifecycle",
    "summary": "AMNUS Core Foundation",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": ["base", "mail", "contacts"],
    "data": [
        "security/ir.model.access.csv",
        "security/amnus_security.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

## 4. Models

- Inherit `models.Model` (persistent), `models.AbstractModel`, or `models.TransientModel` (wizards).
- Model name: `amnus.<module>.<object>` (e.g. `amnus.project.task`).
- `_name`, `_description`, `_inherit` as appropriate.
- Fields: `fields.Char`, `fields.Text`, `fields.Integer`, `fields.Float`, `fields.Date`,
  `fields.Datetime`, `fields.Many2one`, `fields.One2many`, `fields.Many2many`, `fields.Selection`,
  `fields.Boolean`, `fields.Html`, `fields.Binary`, `fields.Monetary`.
- Constraints: Odoo `models.Constraint` or `_sql_constraints`.
- Compute, inverse, search methods follow Odoo API decorators (`@api.depends`, etc.).

## 5. Views & Data

- XML external IDs prefixed with module name (`amnus_core_view_form`).
- Menu items and window actions declared in XML under `data`.
- No hardcoded database IDs in XML.
- Security: `security/ir.model.access.csv` for every model; `security/<module>_security.xml` for
  record rules.

## 6. Security

- Define groups in `security/<module>_groups.xml`.
- Assign access in `ir.model.access.csv` (create/read/write/unlink per group).
- Record rules for row-level access.
- `sudo()` only when justified and documented.
- No credentials in code or docs.

## 7. Internationalization

- Wrap user-facing strings in `_()`.
- `i18n/fr_FR.po` and `i18n/ar_SA.po` required.
- Arabic `ar_SA`: RTL layout in views/CSS; test RTL.
- Production language: `fr_FR`.

## 8. OWL (when required)

- Prefer standard Odoo XML views.
- OWL only for rich client UI.
- Register OWL assets in `__manifest__.py` `assets`.

## 9. Testing

- `tests/__init__.py` + `tests/test_<module>.py` per addon.
- Run with `--test-enable`.
- Tags: `post_install`, `at_install`.
- Test business logic, security (access rights), and critical workflows.

## 10. Versioning & Changelog

- Version pattern: `19.0.<major>.<minor>.<patch>`.
- Update `CHANGELOG.md` on every change.

## 11. Git

- Commit messages: `type(scope): subject`.
- Feature branches off `main`.
- `.gitignore` excludes `__pycache__`, `.pyc`, `*.pyc`, secrets, build artifacts.
