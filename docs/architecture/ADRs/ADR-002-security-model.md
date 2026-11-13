# ADR-002 — AMNUS Security Model

## Status
Accepted — Sprint 01

## Context
AMNUS Core introduces shared models (tags, audit log) that must be protected with
least-privilege access. Audit records must be immutable and protected from forgery.

## Decision
Three AMNUS security groups with an implication hierarchy:

| Group | XML ID | Implies | Access |
|-------|--------|---------|--------|
| AMNUS User | `group_amnus_user` | — | read/write/create tags; no audit log write |
| AMNUS Manager | `group_amnus_manager` | AMNUS User | read audit logs |
| AMNUS Administrator | `group_amnus_admin` | AMNUS Manager | read audit logs |

## Access rights (ir.model.access.csv)
| Model | User | Manager | Admin | Create | Read | Write | Unlink |
|-------|------|---------|-------|--------|------|-------|--------|
| amnus.tag | ✓ | ✓ | ✓ | yes | yes | yes | no |
| amnus.audit.log | — | ✓ | ✓ | no | yes | no | no |

## Audit log immutability
- `amnus.audit.log.write()` and `unlink()` always raise `AccessError`.
- Creation goes through the internal API `log_event()`, which uses controlled
  `sudo()` only inside the implementation so business users can generate audit
  entries without direct write access to the model.
- No unrestricted public method allows forging arbitrary audit records.

## Multi-company
`company_id` present on `amnus.tag` and `amnus.audit.log`; default is
`self.env.company`. Record rules respect company isolation where isolation is
required.

## Consequences
- Ordinary AMNUS users get no Settings or Administration access.
- Audit records are append-only.
- Future business addons call `log_event()` for explicitly defined events only.

## Related
ADR-001 (Core Module)
