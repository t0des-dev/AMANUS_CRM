# Sprint 06.4 — Concurrency & Attachment Security Verification Report

## 1. Executive Summary

Focused runtime verification was performed for the two remaining gaps from Sprint 06.3:

- `NV-01`: genuine concurrent approval execution.
- `NV-02`: attachment HTTP route-level access security.

Results:
- NV-01: **VERIFIED**. Five independent concurrent runs were executed. In every run, exactly one
  approval committed, the other rolled back with `SerializationFailure`, and final state had exactly
  one current assessment and one consistent version snapshot.
- NV-02: **VERIFIED for the tested ORM and HTTP read/mutation scenarios**. Bound attachments were
  accessible only to authorized same-company users and managers; unauthorized and cross-company users
  received `404 Not Found`. Unbound attachments were accessible only to their actual creator.
  Unauthorized write/unlink attempts through JSON-RPC were rejected with `AccessError`, and no
  attachment content was modified.

No implementation defect was demonstrated. No repository implementation file was modified.

Final status: **BOTH VERIFICATION GAPS CLOSED**

## 2. Preflight

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- Database: `amnus_test_19`
- PostgreSQL: 16.14
- Odoo: 19.0 Community Edition
- `git diff --check`: passed
- All pre-existing untracked files and reports preserved.

## 3. Runtime Versions and Test Infrastructure

- Python: 3.12.10
- PostgreSQL: 16.14
- Odoo: 19.0
- HTTP server: `http://127.0.0.1:8079`
- Temporary scripts were kept outside the repository and cleaned up where applicable.

## 4. NV-01 — Source Review

Inspected:
- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
  - `_lock_for_workflow`
  - `action_approve`
  - current-assessment promotion/supersession
  - version snapshot creation

Findings:
- `_lock_for_workflow` locks related Requirement rows first, then all Assessment rows for those
  Requirements.
- `action_approve` acquires the lock before final state checks.
- Authorization is revalidated after lock acquisition.
- Previous current assessment is marked non-current/superseded before promoting the new one.
- Version snapshot creation occurs in the same transaction.
- Failed approval rolls back all related writes.

Database constraint verified:
```text
amnus_fitgap_assessment_current_unique |
CREATE UNIQUE INDEX ... ON public.amnus_fitgap_assessment
USING btree (requirement_id) WHERE (is_current = true)
```

## 5. NV-01 — Genuine Concurrency Methodology

A temporary script outside the repository used:
- independent PostgreSQL cursors via `registry.cursor()`
- independent Odoo environments
- independent transactions
- a `threading.Barrier(2)` to coordinate simultaneous approval calls
- two competing assessment candidates for the same approved Requirement

Each run:
1. Created an approved Requirement.
2. Created two assessment candidates in `under_review`.
3. Committed setup data.
4. Started two threads.
5. Both threads waited at the barrier, then called `action_approve`.
6. Each thread committed or rolled back independently.
7. Final state was inspected in a fresh cursor.
8. Dedicated test records were cleaned up.

No sequential substitute was used.

## 6. NV-01 — Results

Five runs were executed.

| Run | Thread A | Thread B | Final current count | Version count | Final states |
|---:|---|---|---:|---:|---|
| 1 | committed | rolled back (`SerializationFailure`) | 1 | 1 | one approved, one under_review |
| 2 | rolled back (`SerializationFailure`) | committed | 1 | 1 | one approved, one under_review |
| 3 | rolled back (`SerializationFailure`) | committed | 1 | 1 | one approved, one under_review |
| 4 | rolled back (`SerializationFailure`) | committed | 1 | 1 | one approved, one under_review |
| 5 | rolled back (`SerializationFailure`) | committed | 1 | 1 | one approved, one under_review |

Observed exception:
```text
SerializationFailure('could not serialize access due to concurrent update')
```

Interpretation:
- The error is an expected serialization conflict under Odoo/PostgreSQL transaction isolation.
- The failing transaction rolled back completely.
- The successful transaction committed one approval.
- No run produced more than one current assessment.
- No run produced inconsistent version history.
- No partial or contradictory workflow state remained.

## 7. NV-01 — Cleanup Verification

After all runs:
- `res_users` with `nv01_manager_%`: 0
- `project_project` with `NV01 Project`: 0
- `amnus_fitgap_assessment` with `NV01`: 0

All dedicated verification records were cleaned up.

## 8. NV-02 — Source Review

Inspected:
- `amnus.fitgap.assessment.evidence_ids` Many2many to `ir.attachment`.
- `ir.attachment` native access behavior in Odoo 19 Community.
- Fit-Gap ACLs and record rules.
- Native `many2many_binary` widget behavior.
- Odoo 19 `/web/content` route implementation.

Native semantics confirmed:
- For internal users, an attachment bound to `res_model`/`res_id` is readable only if the user has
  read access to the related assessment.
- Unbound attachments are readable only by the system user or creator, unless public or tokenized.
- `/web/content` uses `ir.binary._find_record`, then `record.check_access('read')` for internal users.

## 9. NV-02 — HTTP Test Matrix

Temporary test data was created in `amnus_test_19` and cleaned up afterward.

Identities:
- `nv02_auth_*`: same-company Fit-Gap user
- `nv02_unauth_*`: same-company user without Fit-Gap access
- `nv02_cross_*`: Fit-Gap user in another company
- `nv02_mgr_*`: Fit-Gap manager and attachment creator

Scenarios:
1. Bound attachment with `res_model='amnus.fitgap.assessment'` and correct `res_id`.
2. Unbound attachment with no `res_model`/`res_id`.
3. Unbound attachment created by a normal manager user.

### Bound attachment reads

| User | HTTP result | Body size | Content |
|---|---:|---:|---|
| authorized same-company user | 200 | 5 bytes | `bound` |
| unauthorized user | 404 | 207 bytes | Not Found |
| cross-company user | 404 | 207 bytes | Not Found |
| manager | 200 | 5 bytes | `bound` |

### Unbound attachment reads (system-created)

| User | HTTP result |
|---|---:|
| authorized user | 404 |
| unauthorized user | 404 |
| cross-company user | 404 |
| manager | 404 |

This matches native Odoo behavior: an unbound, non-public attachment is not readable by ordinary users.

### Unbound attachment reads (manager-created)

| User | HTTP result | Body size | Content |
|---|---:|---:|---|
| creator (manager) | 200 | 7 bytes | `unbound` |
| authorized non-creator | 404 | 207 bytes | Not Found |
| unauthorized non-creator | 404 | 207 bytes | Not Found |

### Mutation attempts through JSON-RPC

Unauthorized user attempted:
- `ir.attachment.unlink` on the bound attachment.
- `ir.attachment.write` on the bound attachment.

Results:
- Both returned HTTP 200 with JSON-RPC `AccessError`.
- `unlink` denied read/write access.
- `write` denied write access.
- Bound attachment name remained `bound.txt` after both attempts.

## 10. NV-02 — Cleanup Verification

After cleanup:
- `res_users` with `nv02_%`: 0
- `amnus_fitgap_assessment` with `NV02`: 0

No existing business records were modified.

## 11. Regression and Integrity Checks

Final Fit-Gap test run:
- Command: `odoo-bin ... -u amnus_fitgap --test-enable --test-tags amnus_fitgap --stop-after-init`
- Result: 57 tests, 0 failures, 0 errors.

PostgreSQL partial unique index verified:
```text
amnus_fitgap_assessment_current_unique |
CREATE UNIQUE INDEX ... ON public.amnus_fitgap_assessment
USING btree (requirement_id) WHERE (is_current = true)
```

No test data remained unexpectedly.

## 12. Residual Risks and Limitations

- Concurrency was verified for competing assessment approvals. Other workflow actions were not subjected
  to a separate genuine concurrency test, but they use the same locking strategy.
- HTTP verification covered `/web/content` reads and JSON-RPC write/unlink attempts. It did not
  exercise every possible Odoo route or every attachment mutation route.
- French and Arabic catalogs remain untranslated.
- No visual RTL verification was performed.

## 13. Final Status for NV-01 and NV-02

- `NV-01`: **VERIFIED**
- `NV-02`: **VERIFIED** for the tested ORM and HTTP read/mutation scenarios; broader route-level
  coverage remains a non-blocking informational limitation.

## 14. Final Git Status

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: unchanged at `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `git diff --check`: passed
- No implementation files were modified by this task.
- No commit, merge, or push occurred.
- Only `docs/sprints/SPRINT_06_4_VERIFICATION_REPORT.md` was created by this task.
