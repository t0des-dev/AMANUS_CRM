# Sprint 06.2 — Fit-Gap Audit Remediation Report

## Preflight

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- Database: `amnus_test_19`
- Pre-existing untracked files preserved.

## Findings Remediated

### H-01 — `requirement_id` protected on finalized assessments
- Added `requirement_id` to `CONTENT_FIELDS`.
- Direct writes are now rejected for approved, rejected, cancelled, and superseded assessments.
- Multi-record writes are covered by the same guard.
- Tests added: approved, rejected, cancelled, superseded, and multi-record protection.

### H-02 — Native UI rejection workflow repaired
- Added `action_open_reject_wizard` and a transient wizard
  `amnus.fitgap.assessment.reject.wizard`.
- The Reject button now opens the wizard; `action_reject` still validates and stores the reason.
- Empty reasons are rejected; unauthorized and invalid-state rejections are blocked.
- Tests added for wizard opening and confirmation.

### M-01 / M-02 — Consistent locking and authorization
- `_lock_for_workflow` is now applied to start analysis, submit, approve, reject, cancel,
  and request revision.
- Authorization and state are revalidated after lock acquisition.
- Revision candidate creation is serialized and revalidated.

### M-03 — Attachment access review
- Native Odoo `ir.attachment` comodel access semantics were reviewed and tested.
- Authorized same-company, unauthorized, cross-company, and unbound attachment scenarios were tested.
- No custom override was added because native semantics provide the required protection when
  attachments are bound to the assessment.

### M-04 — `reference` protection
- Direct modification of `reference` is now rejected for all non-superusers.
- Sequence generation and revision candidate creation remain unaffected.

### Low findings
- LOW-01: Remediation report documents the actual transactional order.
- LOW-02: Revision candidate creation now returns a native action to open the candidate.
- LOW-03: `action_start_analysis` now creates an audit event.
- LOW-04: Outcome field help text now describes all eight outcomes.

## Tests Added

- Requirement ID protection tests (approved, rejected, cancelled, superseded, multi-record).
- Reference immutability test.
- Rejection through record reason, empty reason, unauthorized, and invalid state tests.
- Reject wizard open and confirm tests.
- Attachment authorized/unauthorized/cross-company/unbound tests.

## Verification

- `amnus_fitgap`: 57 tests, 0 failures, 0 errors.
- `amnus_analysis`: 58 tests, 0 failures, 0 errors.
- `amnus_core`: 34 tests, 0 failures, 0 errors.
- `amnus_crm`: 23 tests, 0 failures, 0 errors.
- `amnus_projects`: 61 tests, 0 failures, 0 errors.
- `amnus_agile`: 98 tests, 0 failures, 0 errors.
- Total: 331 tests, 0 failures, 0 errors.
- Python compilation: passed.
- XML parsing: passed.
- Manifest and CSV: valid.
- POT/PO syntax: valid (202 entries each).
- PostgreSQL partial unique index verified.

## Concurrency

Genuine concurrent execution was not implemented in this remediation. NV-01 remains explicitly
unresolved and is not claimed as verified. The locking strategy is source-reviewed and serialized
through PostgreSQL row locks, but runtime concurrency proof is still pending.

## Translation Status

Catalogs were regenerated from the actual module. Entries are extracted but remain untranslated
in French and Arabic. No translations were fabricated.

## Unresolved Findings

- `NV-01`: Genuine concurrent approval execution remains unverified.
- `NV-02`: Attachment route-level access was tested through ORM and documented native semantics,
  but not every HTTP route was exhaustively exercised.

## Final Git Status

No commits, merges, or pushes were performed. Only remediation changes and this report were added.

## Final Status

`REMEDIATION COMPLETE — READY FOR INDEPENDENT AUDIT`
