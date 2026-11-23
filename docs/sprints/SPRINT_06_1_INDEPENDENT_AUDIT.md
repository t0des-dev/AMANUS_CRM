# Sprint 06.1 — Independent Security, Architecture & Quality Audit

## 1. Executive Summary

Sprint 06 implementation is substantially complete and broadly consistent with the approved
architecture. The current-assessment invariant is correctly enforced at the PostgreSQL level,
immutable version snapshots are protected, core workflow transitions are server-side guarded,
and the new and regression test suites pass.

However, the audit identified two High-severity findings and several Medium/Low findings.
The most significant are:

1. An approved assessment's `requirement_id` is not protected from direct writes, allowing a
   manager to move an approved assessment to another requirement and undermine traceability,
   company/project consistency, and the current-assessment invariant.
2. Rejection cannot be completed through the native UI because `action_reject` requires a
   reason argument that the form button does not supply and the method does not read from the
   record.

No Critical finding was identified. Database-level current-assessment uniqueness, atomic
replacement, snapshot immutability, and basic multi-company isolation are verified.

Final recommendation: **APPROVED WITH REQUIRED FIXES**.

## 2. Audit Scope and Methodology

Audit-only. No repository files were modified except this report. No commits, merges, or pushes
were performed. Runtime verification used only `amnus_test_19`.

Methods:
- Read-only source inspection of `addons/amnus/amnus_fitgap/`.
- Comparison against approved architecture and Sprint 05.2 decisions.
- Read-only PostgreSQL inspection of indexes and schema.
- Sequential execution of existing test suites against `amnus_test_19`.
- Static validation of Python, XML, CSV, and PO files.
- Review of Odoo 19 Community attachment and record-rule semantics.

## 3. Branch/Base/HEAD Verification

- Branch: `feature/sprint-06-amnus-fitgap`
- HEAD: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- `main`: `afbd6b357e40ce38349e7f79e9ce5ecc8e02acfd`
- Feature branch is based on the approved main baseline.
- `git diff --check`: no whitespace errors.
- Pre-existing untracked files and reports were preserved.

## 4. Source Files Inspected

- `addons/amnus/amnus_fitgap/__manifest__.py`
- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
- `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment_version.py`
- `addons/amnus/amnus_fitgap/security/amnus_fitgap_groups.xml`
- `addons/amnus/amnus_fitgap/security/amnus_fitgap_security.xml`
- `addons/amnus/amnus_fitgap/security/ir.model.access.csv`
- `addons/amnus/amnus_fitgap/views/amnus_fitgap_assessment_views.xml`
- `addons/amnus/amnus_fitgap/views/amnus_fitgap_menus.xml`
- `addons/amnus/amnus_fitgap/data/amnus_fitgap_sequence.xml`
- `addons/amnus/amnus_fitgap/tests/*`
- `addons/amnus/amnus_fitgap/i18n/*`
- `docs/sprints/SPRINT_06_IMPLEMENTATION_REPORT.md`
- `docs/architecture/AMNUS_FITGAP_ARCHITECTURE.md`
- `docs/sprints/SPRINT_05_2_DECISIONS.md`

## 5. Database and Runtime Verification

PostgreSQL inspection confirmed:

```text
amnus_fitgap_assessment_current_unique |
CREATE UNIQUE INDEX ... ON public.amnus_fitgap_assessment
USING btree (requirement_id) WHERE (is_current = true)
```

The index exists, targets the correct table/column, and is partial on `is_current = TRUE`.

Runtime test results (sequential, `amnus_test_19` only):

| Suite | Tests | Failures | Errors |
|---|---:|---:|---:|
| `amnus_fitgap` | 41 | 0 | 0 |
| `amnus_analysis` | 58 | 0 | 0 |
| `amnus_core` | 34 | 0 | 0 |
| `amnus_crm` | 23 | 0 | 0 |
| `amnus_projects` | 61 | 0 | 0 |
| `amnus_agile` | 98 | 0 | 0 |
| **Total** | **315** | **0** | **0** |

The implementation report's claimed totals are accurate.

## 6. Architecture and Dependency Findings

- Direct dependencies are exactly `amnus_core` and `amnus_analysis`. Approved.
- No direct dependency on `amnus_agile`, `amnus_projects`, `documents`, or `helpdesk`. Approved.
- `project` and `mail` are obtained transitively through `amnus_analysis`; this is consistent with
  the approved architecture, although `amnus_fitgap` does use `project.project` and `mail.thread`.
- No Enterprise dependencies or OWL/JavaScript were found.
- No dependency cycle was identified from the manifest graph.

Finding: none blocking.

## 7. Current Assessment Integrity Findings

Verified:
- `is_current` marker exists and is indexed.
- Partial unique index exists and is correct.
- Candidate assessments are created with `is_current = False`.
- Approved assessment remains current while a replacement candidate is drafted/reviewed.
- Successful replacement approval supersedes the previous assessment and promotes the new one.
- Rejected and cancelled candidates remain non-current.
- Manual duplicate current assessment is rejected by PostgreSQL.

The invariant is database-enforced, not ORM-only.

## 8. Concurrency and Atomic Replacement Findings

### Verified by source

- `_lock_for_workflow` locks the related Requirement and all assessments for that requirement.
- Locking occurs before final state checks in `action_approve`.
- Previous current assessment is marked non-current/superseded before promoting the new one.
- Version snapshot creation, state promotion, and superseding occur in the same transaction.
- Failed approval rolls back the transaction.

### Not verified

- No genuine concurrent execution test exists. The existing `test_concurrent_approval_not_duplicate_current`
  test was changed to a sequential replacement scenario and therefore does not prove concurrency safety.
- Authorization is checked before locking and is not revalidated after lock acquisition.

Finding ID: `INFO-01` / `NV-01` — Concurrency is source-supported but not independently
runtime-verified.

## 9. Version Snapshot and Immutability Findings

Verified:
- Snapshot is created on approval only.
- `write()` and `unlink()` always raise `UserError`, including for managers.
- Direct creation by non-superuser raises `UserError`.
- Snapshot includes outcome, capability references, gap analysis, solution details, all five effort
  categories, total effort, confidence, risk, decision rationale, approval metadata, requirement,
  project, customer, and company context.
- Version numbering is sequential per approval.

No omitted business-significant approved field was identified.

## 10. Workflow Findings

Verified server-side:
- Valid transitions succeed.
- Invalid transitions raise `UserError`.
- Direct state writes are rejected for non-superusers.
- Approval requires manager authorization.
- Rejection requires a reason.
- Approved content and effort values cannot be modified.
- Revision creates a new non-current candidate.
- Previous approved assessment remains immutable and current until replacement approval.
- Superseded and cancelled records preserve history.
- Deletion protects approved/rejected/cancelled/superseded assessments.

### Finding H-02 (HIGH)

- File: `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
- Method: `action_reject(self, rejection_reason=None)`
- View: `amnus_fitgap_assessment_views.xml`, Reject button
- Evidence: The form's Reject button calls `action_reject` without passing `rejection_reason`. The
  method does not read `self.rejection_reason`; therefore every UI rejection fails with
  "A rejection reason is required."
- Impact: Managers cannot reject assessments through the native UI despite the workflow requiring it.
- Remediation direction: bind the rejection reason from the record (or introduce a small wizard),
  while retaining server-side validation.

### Finding M-01 (MEDIUM)

- File: `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
- Methods: `action_approve`, `action_reject`, `action_cancel`, `action_request_revision`
- Evidence: Manager authorization is checked before `_lock_for_workflow` and is not revalidated after
  locking. Reject/cancel/request-revision do not acquire locks at all.
- Impact: authorization and state checks can be stale under concurrent operations.
- Remediation direction: revalidate authorization after locking and serialize all state-changing actions.

### Finding M-02 (MEDIUM)

- File: `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
- Method: `action_request_revision`
- Evidence: No locking or state revalidation occurs before candidate creation.
- Impact: A candidate can be created from an assessment whose state changed concurrently.
- Remediation direction: acquire the workflow lock and revalidate state before creating the candidate.

## 11. Security and Multi-Company Findings

Verified:
- Group hierarchy is correct: user → manager → admin.
- Groups are not auto-assigned.
- ACL matrix matches intended roles.
- Version snapshots are read-only to ordinary users.
- Company isolation record rule is global and AND-combined with group rules.
- Project visibility rule follows the established AMNUS pattern.
- Cross-company assessment access is denied for ordinary users.
- Cross-company manager isolation is source-supported by the global company rule.

No cross-company leakage was demonstrated.

### Finding M-03 (MEDIUM)

- File: `addons/amnus/amnus_fitgap/security/amnus_fitgap_security.xml`
- Rules: assessment and version attachment-related access
- Evidence: Attachment access is delegated entirely to native Odoo `ir.attachment` comodel checks.
  No Fit-Gap-specific attachment rule or override exists.
- Impact: If an attachment is created without `res_model`/`res_id`, access behavior may be
  inconsistent with assessment-level authorization.
- Remediation direction: document and, if needed, enforce assessment-level attachment access
  explicitly while preserving native Odoo semantics.

## 12. Attachment Access Findings

Verified by source and one runtime test:
- An attachment linked with `res_model='amnus.fitgap.assessment'` and a valid `res_id` is readable
  by a Fit-Gap user with access to that assessment.
- A cross-company user cannot read such an attachment.

Not verified:
- Direct `/web/content` access for all attachment states.
- Attachments created without `res_model`/`res_id`.
- Attachment modification/unlink through generic routes.

Finding: `NV-02` — Attachment route-level behavior was not exhaustively runtime-tested.

## 13. Odoo 19 UI Compatibility Findings

Verified:
- XML parses successfully.
- Views reference existing fields and methods.
- Statusbar values match workflow states.
- Search filters and group-by definitions are valid.
- Menus are placed under the AMNUS root.
- No OWL, custom JavaScript, Enterprise-only widgets, or unnecessary CSS were found.
- Approved content is presented readonly in the form.

Finding: `H-02` also applies as a UI workflow defect (see section 10).

## 14. Outcome and Estimation Findings

Verified:
- Exactly eight outcome values.
- Exactly five effort categories.
- No legacy six-category fields.
- No `approval_status` field.
- `total_effort` is computed from all five categories and is readonly.
- Negative effort values are rejected by server-side constraint.
- Outcome and workflow state are separate fields.

Minor observation: help text for outcome values and `deferred`/`requires_analysis` is generic.
Finding: `LOW-04`.

## 15. Test Quality and Execution Results

All 41 new tests pass, along with all 274 claimed regression tests (315 total, zero failures).

Test quality strengths:
- Current-assessment uniqueness is tested at the database level.
- Version immutability is tested.
- Security ACLs and cross-company visibility are tested.
- Workflow transitions are tested.

Test quality weaknesses:
- No genuine concurrent approval test.
- `test_current_unique_index` uses a broad `Exception` catch.
- `test_concurrent_approval_not_duplicate_current` was converted to a sequential scenario and
  therefore does not validate concurrency.
- UI rejection path is not tested.

## 16. Translation Validation Results

Catalogs validated with `polib`:
- `amnus_fitgap.pot`: 196 entries
- `fr_FR.po`: 196 entries
- `ar_SA.po`: 196 entries

Syntax is valid. Source-to-catalog comparison was not fully recalculated beyond Odoo export, but
the catalogs were generated from the actual module. Translations are currently untranslated
(msgstr equals msgid in generated files), so "complete coverage" means extraction coverage, not
linguistic translation quality.

Finding: `INFO-03` — French and Arabic linguistic translations are not yet populated.
Finding: `INFO-04` — No visual RTL verification was performed.

## 17. Audit Logging Findings

Verified:
- Submission, approval, rejection, cancellation, and revision candidate creation are logged.
- Actor is derived from `self.env.user`.
- Company is derived from `self.env.company`.
- Audit records are immutable.

Observation: `action_start_analysis` does not log an audit event. This is a minor consistency gap.
Finding: `LOW-03`.

## 18. Documentation Consistency Findings

Documentation generally matches implementation. The implementation report's test totals and
dependency claims are accurate. One documentation gap: the report describes atomic replacement
order as snapshot creation before promotion, while the implementation marks the previous
assessment superseded and promotes the new assessment before creating the snapshot. All steps
remain transactional, so this is an ordering documentation mismatch rather than an integrity defect.

Finding: `LOW-01`.

## 19. Residual Risks and Unverified Areas

- Genuine concurrent approval was not runtime-tested.
- Attachment access via all Odoo routes was not exhaustively tested.
- UI rejection is currently unusable.
- Approved `requirement_id` mutability is an integrity risk.
- French/Arabic translations are untranslated.
- Visual RTL layout was not inspected.

## 20. Severity-Classified Findings

### Critical (0)

None.

### High (2)

- `H-01` — Approved assessment `requirement_id` is not protected from direct writes.
  - File: `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`
  - Method: `write`
  - Evidence: `CONTENT_FIELDS` does not include `requirement_id`, and the write guard only
    special-cases `project_id`, not `requirement_id`.
  - Impact: Approved assessment can be moved to another requirement, breaking traceability,
    company/project consistency, and current-assessment semantics.
  - Remediation direction: add `requirement_id` to protected fields and block changes in
    approved/rejected/cancelled/superseded states.

- `H-02` — Rejection cannot be completed through the native UI.
  - File: `addons/amnus/amnus_fitgap/models/amnus_fitgap_assessment.py`,
    `addons/amnus/amnus_fitgap/views/amnus_fitgap_assessment_views.xml`
  - Method: `action_reject`
  - Evidence: Reject button calls `action_reject` without a reason; method requires
    `rejection_reason`.
  - Impact: Managers cannot reject assessments through the standard form.
  - Remediation direction: read the reason from the record or introduce a rejection wizard,
    retaining server-side validation.

### Medium (4)

- `M-01` — Authorization is not revalidated after locking.
- `M-02` — Reject, cancel, submit, and revision actions are not consistently serialized.
- `M-03` — Attachment access depends entirely on native comodel semantics.
- `M-04` — `reference` is mutable through direct write despite being conceptually immutable.

### Low (4)

- `LOW-01` — Documented atomic replacement order differs from implementation order.
- `LOW-02` — Revision candidate creation does not navigate to the new record.
- `LOW-03` — `action_start_analysis` does not create an audit event.
- `LOW-04` — Outcome help text is generic.

### Info (4)

- `INFO-01` — Concurrency is source-supported but not runtime-tested.
- `INFO-02` — Native widget sets attachment `res_model`/`res_id`.
- `INFO-03` — French and Arabic catalogs are extracted but untranslated.
- `INFO-04` — No visual RTL verification was performed.

### Not Verified (2)

- `NV-01` — Genuine concurrent approval execution.
- `NV-02` — Attachment route-level access for all creation paths.

## 21. Final Recommendation

**APPROVED WITH REQUIRED FIXES**

The implementation is safe to retain and is architecturally sound, with database-enforced
current-assessment uniqueness and passing tests. However, the two High findings
(`H-01`, `H-02`) and Medium findings should be remediated before merge.

No Critical finding was identified. No material architecture deviation was found.
No commit, merge, or push was performed. Only `docs/sprints/SPRINT_06_1_INDEPENDENT_AUDIT.md`
was created by this audit.
