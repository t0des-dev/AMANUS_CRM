# Sprint 06.3 — Independent Fit-Gap Remediation Re-Audit

## 1. Executive Summary

Sprint 06.2 remediation successfully resolved the two High findings and the targeted Medium/Low
findings from Sprint 06.1. The implementation now protects finalized `requirement_id` and
`reference` values, provides a native rejection wizard, applies consistent locking and
authorization revalidation, and documents the actual transactional behavior.

The core data-integrity invariants are verified:
- PostgreSQL partial unique index is present and correct.
- Version snapshots are immutable and complete.
- Workflow transitions are server-side guarded.
- Regression and Fit-Gap tests pass.

Two verification gaps remain open by design:
- `NV-01`: genuine concurrent approval execution was not performed.
- `NV-02`: HTTP route-level attachment access was not exhaustively exercised.

No Critical or High finding remains. No material architecture deviation was found.

Final recommendation: **APPROVED WITH REQUIRED FIXES** (required follow-up verification only;
no code change is currently evidenced as necessary).

## 2. Preflight

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- Database used for verification: `amnus_test_19`
- `git diff --check`: passed
- Pre-existing untracked files and reports preserved.

## 3. Source Files Inspected

- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment_reject_wizard.py`
- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment_version.py`
- `addons/amnus/amnus_fitgap/security/*`
- `addons/amnus/amnus_fitgap/views/*`
- `addons/amnus/amnus_fitgap/tests/*`
- `addons/amnus/amnus_fitgap/i18n/*`
- `docs/sprints/SPRINT_06_1_INDEPENDENT_AUDIT.md`
- `docs/sprints/SPRINT_06_2_REMEDIATION_REPORT.md`

## 4. Finding Reconciliation

| Finding | Status | Notes |
|---|---|---|
| H-01 | RESOLVED | `requirement_id` added to `CONTENT_FIELDS`; finalized records protected; tests pass. |
| H-02 | RESOLVED | Native wizard added; `action_reject` validates and stores reason; tests pass. |
| M-01 | RESOLVED | Authorization revalidated after lock in approve/reject/revision. |
| M-02 | RESOLVED | All state-changing actions acquire `_lock_for_workflow`. |
| M-03 | PARTIALLY RESOLVED | Native semantics reviewed and ORM-tested; HTTP routes not fully exercised. |
| M-04 | RESOLVED | `reference` direct writes rejected for non-superusers. |
| LOW-01 | RESOLVED | Documentation updated to actual transactional order. |
| LOW-02 | RESOLVED | Revision candidate creation returns a native open action. |
| LOW-03 | RESOLVED | `action_start_analysis` now logs an audit event. |
| LOW-04 | RESOLVED | Outcome help text describes all eight outcomes. |
| INFO-01 | OPEN / NOT VERIFIED | Concurrency remains source-reviewed only. |
| INFO-02 | SOURCE-REVIEWED | Native widget binds attachments to parent `res_model`/`res_id`. |
| INFO-03 | OPEN / INFORMATIONAL | French and Arabic catalogs remain untranslated. |
| INFO-04 | NOT VERIFIED | No visual RTL inspection performed. |
| NV-01 | NOT VERIFIED | No genuine concurrent execution test exists. |
| NV-02 | PARTIALLY VERIFIED | ORM and cross-company tests pass; HTTP routes not exercised. |

## 5. H-01 Verification

Evidence:
- `CONTENT_FIELDS` includes `requirement_id`.
- `write()` raises `UserError` for non-superusers when content fields are written on
  approved/rejected/cancelled/superseded assessments.
- Multi-record writes use the same guard.

Tests:
- `test_requirement_id_protected_on_finalized`
- `test_requirement_id_protected_approved`
- `test_requirement_id_protected_cancelled`
- `test_requirement_id_protected_superseded`
- `test_multi_record_requirement_id_protected`

Result: all pass.

## 6. H-02 Verification

Evidence:
- Form Reject button now calls `action_open_reject_wizard`.
- Wizard model requires `rejection_reason`.
- `action_reject` reads the reason from the record when invoked through the wizard and validates
  non-empty values.
- Underlying method remains protected by manager authorization and state checks.
- Audit event is created on rejection.

Tests:
- `test_reject_wizard_opens`
- `test_reject_wizard_confirms`
- `test_rejection_via_record_reason`
- `test_rejection_empty_reason_rejected`
- `test_rejection_unauthorized`
- `test_rejection_invalid_state`

Result: all pass.

## 7. Locking and Authorization Matrix

| Method | Acquires lock | Revalidates authorization | Revalidates state | Transaction-safe | Result |
|---|---|---|---|---|---|
| `action_start_analysis` | Yes | N/A (user-level ACL) | Yes | Yes | Verified by source/tests |
| `action_submit_for_review` | Yes | N/A (user-level ACL) | Yes | Yes | Verified by source/tests |
| `action_approve` | Yes | Yes | Yes | Yes | Verified by source/tests |
| `action_reject` | Yes | Yes | Yes | Yes | Verified by source/tests |
| `action_cancel` | Yes | Yes for under-review | Yes | Yes | Verified by source/tests |
| `action_request_revision` | Yes | Yes | Yes | Yes | Verified by source/tests |

Lock order is consistent: Requirement rows first, then Assessment rows.

## 8. Concurrency Evidence and NV-01

No genuine concurrent test exists. The test named `test_concurrent_approval_not_duplicate_current`
is sequential and therefore does not prove concurrency safety.

Source evidence:
- `_lock_for_workflow` locks the related Requirement and all assessments for that requirement.
- Approval marks the previous current assessment non-current before promoting the new one.
- The partial unique index remains the final database-level guard.

NV-01 remains **NOT VERIFIED**. The locking design is sound by inspection, but runtime concurrency
proof is still missing.

## 9. Attachment ORM/HTTP Evidence and NV-02

ORM tests passed:
- Authorized same-company user can read a bound attachment.
- Unauthorized user cannot read it.
- Cross-company user cannot read it.
- Unbound attachment is readable only by its creator.

Source review:
- Native Odoo `ir.attachment` access checks use `res_model`/`res_id` comodel access.
- The standard `many2many_binary` widget binds uploaded attachments to the parent assessment.

Not tested:
- Direct `/web/content` requests for every attachment state.
- Route-level modification/deletion paths.
- Attachments created through every possible client path.

NV-02 remains **PARTIALLY VERIFIED**.

## 10. `reference` Immutability Evidence

- `reference` is generated by the `amnus.fitgap.assessment` sequence.
- Direct writes by non-superusers raise `UserError`.
- Multi-record writes are covered by the same guard.
- Revision candidates receive new sequence-generated references.

Test: `test_reference_immutable` passes.

## 11. Current-Assessment and Snapshot Integrity

Verified:
- `is_current` marker and partial unique index are present.
- Only successful approval supersedes and promotes.
- Rejected/cancelled candidates remain non-current.
- Approved assessments remain current while candidates are drafted/reviewed.
- Version snapshots are immutable and contain all approved business-significant fields.
- Revision creates a new candidate without mutating the prior approved assessment or snapshot.

## 12. Test-Quality Review and Execution Results

Tests are meaningful and target server-side enforcement rather than UI visibility. New tests cover
the remediated High/Medium findings and attachment access.

Executed sequentially against `amnus_test_19` only:

| Suite | Tests | Failures | Errors |
|---|---:|---:|---:|
| `amnus_fitgap` | 57 | 0 | 0 |
| `amnus_analysis` | 58 | 0 | 0 |
| `amnus_core` | 34 | 0 | 0 |
| `amnus_crm` | 23 | 0 | 0 |
| `amnus_projects` | 61 | 0 | 0 |
| `amnus_agile` | 98 | 0 | 0 |
| **Total** | **331** | **0** | **0** |

The reported counts match the Sprint 06.2 remediation report.

Weaknesses noted:
- No genuine concurrent test.
- Some tests use broad `Exception` catches.
- HTTP route-level attachment behavior is not exercised.

## 13. Architecture, Dependency, and Scope Review

Verified:
- Direct dependencies remain exactly `amnus_core` and `amnus_analysis`.
- No Agile, Projects, Documents, Helpdesk, or Enterprise dependency was added.
- No dependency cycle was identified.
- No OWL or JavaScript was introduced.
- `project` and `mail` usage remains transitive through `amnus_analysis`.
- No scope drift from Sprint 05.2 decisions was identified.

## 14. Documentation and Translation Status

Verified:
- Sprint 06.2 report matches the source implementation.
- Atomic replacement order is documented accurately.
- Reject wizard is documented.
- Locking and authorization behavior are described accurately.
- Attachment limitations are disclosed, not overstated.
- POT/PO syntax is valid.

Catalog status:
- `amnus_fitgap.pot`: 202 entries
- `fr_FR.po`: 202 entries
- `ar_SA.po`: 202 entries

French and Arabic catalogs remain untranslated. Extraction coverage is complete; linguistic
translation is not.

No visual RTL verification was performed.

## 15. Residual Risks

1. `NV-01`: Genuine concurrent approval is not runtime-verified. Locking and the partial index
   provide strong protection, but a coordinated concurrency test is still needed.
2. `NV-02`: HTTP route-level attachment behavior is not fully verified.
3. French and Arabic translations remain untranslated.
4. No visual RTL verification was performed.

## 16. Final Recommendation

**APPROVED WITH REQUIRED FIXES**

No Critical or High findings remain. All material Medium findings are resolved. The remaining
items are verification gaps (NV-01, NV-02) and informational/non-blocking items. Required
follow-up verification should be completed before final merge confidence, but no code change is
currently evidenced as necessary.

## 17. Final Git Status

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: unchanged at `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `git diff --check`: passed
- No commit, merge, or push occurred.
- Only `docs/sprints/SPRINT_06_3_INDEPENDENT_RE_AUDIT.md` was created by this audit.
