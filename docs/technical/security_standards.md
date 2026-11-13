# Security Standards — AMNUS

## 1. Access Rights

- Every model must have an entry in `security/ir.model.access.csv`.
- Columns: `id`, `name`, `model_id:id`, `group_id:id`, `perm_create`, `perm_read`, `perm_write`,
  `perm_unlink`.
- Grant permissions per functional group, not per user.

## 2. Record Rules

- Use `security/<module>_security.xml` for row-level access control.
- Define domain filters (e.g. company isolation, user ownership).
- Multi-company (`res.company`) aware where applicable.

## 3. Security Groups

- Define groups in `security/<module>_groups.xml`.
- Groups inherit from `base.group_user` / `base.group_system` as appropriate.
- Document each group's purpose.

## 4. Privileged Operations

- `sudo()` only when justified and documented (e.g. system cron, audit logging).
- Never use `sudo()` to silently bypass access rights in user-facing flows.
- Review every `sudo()` usage during code review.

## 5. Secrets & Credentials

- No passwords, API keys, or tokens in source code or documentation.
- Use Odoo `ir.config_parameter` (system parameters) or environment variables for secrets.
- Config files contain placeholder passwords (`CHANGE_ME_*`) — replace per environment, never commit.

## 6. Controllers & Endpoints

- Website-facing controllers must validate input and check access rights.
- CSRF protection where Odoo provides it.
- File upload: validate MIME type, size, magic bytes.
- Protect against SSRF in outbound HTTP requests.

## 7. Data Protection

- GDPR considerations: right to access/erasure where personal data is stored.
- Audit log for sensitive operations (discounts, cancellations, deletions).
- Do not log passwords or secrets.

## 8. Code Review Checklist

- [ ] Access rights declared for all new models
- [ ] Record rules defined where row-level control is needed
- [ ] No hardcoded credentials
- [ ] `sudo()` usage justified and documented
- [ ] Input validation on controllers
- [ ] No direct SQL unless justified

## 9. Compliance

- LGPL-3 license (Odoo Community).
- OWASP best practices for web-facing features.
- Odoo security guidelines.
