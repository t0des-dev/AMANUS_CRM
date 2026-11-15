# SPRINT 04.2 — Security & Data Integrity Remediation

Date: 2026-11-15  
Branch: `feature/sprint-04-amnus-agile`  
Base (audited implementation) commit: `5b7ac38d0a92a9fdc1ed63f85c0e5febc7cca15d`  
Audit reference: `docs/sprints/SPRINT_04_1_AUDIT.md` (unchanged)

## 1. Scope

Controlled remediation of confirmed Sprint 04.1 findings without redesigning the
`amnus_agile` addon. Focus: server-side workflow enforcement, historical/frozen
metric protection, Story/Task integrity, append-only history, burndown event
correctness, and regression coverage.

## 2. Finding remediation map (F-01–F-09 mandatory)

| Finding | Severity | Source / affected | Corrective change | Regression test(s) | Verification |
|---|---|---|---|---|---|
| F-01 Frozen metrics writable | CRITICAL | `amnus_agile/models/amnus_agile_sprint.py` (`baseline_points`, `final_*`, `create`, `write`, `unlink`) | Direct ORM/RPC `write` blocks `state` and all frozen snapshot fields; `create` rejects non-draft state and any fabricated frozen values; closed/cancelled sprint metrics immutable; snapshots set only via internal workflow write (`_internal_write`) during validated `action_start/close/cancel`; closed/cancelled sprints cannot be deleted. | `test_f01_manager_cannot_write_final_metrics_on_closed_sprint`, `test_f01_closed_sprint_metrics_unchanged_after_later_story_edit`, `test_f01_cannot_create_sprint_with_fabricated_frozen_values`, `test_f05_cannot_unlink_closed_sprint` | Covered by new remediation tests and existing freeze/velocity tests |
| F-02 Task move/cross-company leak | CRITICAL | `amnus_agile/models/amnus_agile_user_story.py` (`task_state`, `task_user_ids`, compute), `amnus_projects/models/project_task.py` (`write`) | `task_state`/`task_user_ids` replaced with access-safe computed fields (`compute_sudo=False`) that omit values when linked task is not readable; task-side guard rejects moving/removing project of a task linked to an Agile story across project/company while link exists; story-side project/company constraints retained. | `test_f02_cannot_link_task_from_other_project`, `test_f02_cannot_move_linked_task_to_other_project`, `test_f02_cannot_move_linked_task_to_other_company`, `test_f02_inaccessible_task_state_not_disclosed`, existing `test_linked_task_must_belong_to_same_project`, `test_task_can_only_link_to_one_story` | Guard on both sides; no sudo disclosure |
| F-03 Sprint state bypass | HIGH | `amnus_agile_sprint.py` (`write`, `action_*`) | Direct `write({'state': ...})` always rejected; transitions only through authorized action methods using locked, validated internal writes; closure/start/cancel/plan side effects (snapshots, memberships, events, audit) executed in workflow; repeated closure rejected. | `test_f03_direct_write_state_close_rejected`, `test_f03_direct_write_state_start_and_cancel_rejected`, `test_f03_repeated_close_rejected`, existing lifecycle tests | UserError on direct transition |
| F-04 Unguarded create | HIGH | `amnus_agile_sprint.py` (`create`), `amnus_agile_user_story.py` (`create`) | Sprint create forced to draft with no frozen values; story create rejects done state, rejects non-backlog/planned states, rejects assignment to closed/cancelled sprint, validates project/company; no fabricated workflow history. | `test_f04_cannot_create_closed_sprint`, `test_f04_cannot_create_done_story_directly`, `test_f04_cannot_create_story_in_closed_sprint`, `test_f09_cannot_create_story_in_progress_state` | Direct ORM create guarded |
| F-05 Unguarded unlink/cascade loss | HIGH | `amnus_agile_sprint.py`, `amnus_agile_user_story.py`, `amnus_agile_membership.py`, `amnus_agile_burndown.py`, `amnus_agile_epic.py` | Closed/cancelled sprints cannot be deleted; sprints/stories with historical membership/burndown history cannot be deleted (archive instead); stories in closed/cancelled sprints cannot be deleted; membership and burndown unlink blocked (defense-in-depth); epic with stories cannot be deleted. | `test_f05_cannot_unlink_closed_sprint`, `test_f05_cannot_unlink_story_with_membership_history`, membership read-only tests retained | Historical records preserved |
| F-06 Story target sprint state unchecked | HIGH | `amnus_agile_user_story.py` (`create`, `write`, `_validate_sprint_assignment`), `amnus_agile_sprint.py` (`action_add_stories`) | Assignment to closed/cancelled sprint rejected on direct create, direct write, action add, and sprint bulk add; membership open/close and burndown events synchronized. | `test_f06_direct_write_to_closed_sprint_rejected`, existing `test_add_to_closed_sprint_is_rejected`, `test_f04_cannot_create_story_in_closed_sprint` | Target state validated in all paths |
| F-07 Carry-over rewrites closed history | HIGH | `amnus_agile_sprint.py` (`action_carry_over`), `amnus_agile_user_story.py` (`_workflow_carry_over`), membership guards | Carry-over rejected if source sprint is closed/cancelled; only open source membership closed as `carried_over`; closed membership rows immutable (`write`/`_close`/`_mark_committed` reject closed rows); target gets a new open membership. | `test_f07_carry_over_from_closed_sprint_rejected`, existing `test_carry_over_preserves_membership_history` | No rewrite of closed source rows |
| F-08 Burndown missing events | HIGH | `amnus_agile_burndown.py` (event model), `amnus_agile_sprint.py` (`_record_burndown_event`, workflow/event hooks), `amnus_agile_user_story.py` (point/scope/state hooks) | Burndown converted to append-only dated events with type/story/before/after/sequence and deterministic ordering; events recorded for baseline, scope add/remove, re-estimation, start, completion, carry-over in/out, cancellation, closure; daily carry-forward series helper added. | `test_f08_day1_to_day5_burndown_scenario`, `test_f08_series_carries_forward_event_free_days`, `test_f11_burndown_events_have_deterministic_ordering`, existing burndown tests | Day 1–5 progression `[8,3,5,7,2]` recorded |
| F-09 Story create/write workflow bypass | HIGH | `amnus_agile_user_story.py` (`create`, `write`, `_workflow_transition`, actions) | Direct `state` writes rejected (must use workflow actions); create restricted to backlog/planned and validated; completion requires acceptance criteria in workflow; audit logging and burndown side effects executed in controlled transitions/handlers; safe planning fields remain editable by managers. | `test_f09_direct_write_done_rejected`, `test_f09_cannot_create_story_in_progress_state`, existing transition/acceptance tests | No direct state bypass |

## 3. MEDIUM/LOW/INFO assessment

| Finding | Severity | Action | Rationale / notes |
|---|---|---|---|
| F-10 same-state transition blocks planned add/carry | MEDIUM | Fixed | Same-state direct writes ignored; workflow transitions idempotent where safe; planned story can be added without `planned->planned` error. Test: `test_f10_add_already_planned_story_to_sprint`. |
| F-11 burndown date uniqueness/concurrency | MEDIUM | Fixed (design) | Event model uses unique `(sprint_id,date,event_sequence)` with server-side sequence allocation; deterministic ordering `date,event_sequence,id`. Concurrency race test not added (requires parallel transactions). |
| F-12 sprint closure/start/cancel races | MEDIUM | Partially fixed | Row locking (`SELECT ... FOR UPDATE`) added for workflow transitions/start/close/cancel/carry-over to serialize state and metric capture. DB terminal-state constraint not added. No concurrency stress test. |
| F-13 burndown project visibility rule | MEDIUM | Fixed | Added `group_amnus_agile_user` project-visibility record rule for burndown. Test: `test_f13_burndown_hidden_from_non_follower_user`. |
| F-14 membership re-entry rewrites history | MEDIUM | Fixed | Re-adding a story to a sprint with existing historical membership row is rejected (preserves append-only history, avoids stale `final_points` rewrite). Test: `test_f14_story_cannot_reenter_same_sprint_after_removal`. |
| F-15 epic state write guard | LOW | Fixed | Direct epic `state` writes rejected; workflow action required. Test: `test_f15_epic_state_cannot_be_written_directly`. |
| F-16 capacity non-negative | LOW | Fixed | Added constraint rejecting negative `capacity_points`. Test: `test_f16_negative_capacity_rejected`. |
| F-17 event-free days carry-forward | LOW | Addressed | `get_burndown_series()` returns continuous daily series carrying last known values forward; events are recorded for scope/re-estimation/carry-over so missing-event gaps reduced. Test: `test_f08_series_carries_forward_event_free_days`. |
| F-18–F-24 | INFO | No code change | Confirmed clean by audit (rule semantics, RPC private methods, sudo user preservation, constraints/API/i18n). Preserved. |

## 4. Security and integrity guarantees

- Sprint `state` and frozen fields (`baseline_points`, `final_*`) are not writable via direct ORM/RPC; internal workflow uses parent `write` only after authorization/validation.
- Burndown and membership histories are append-only from clients (ACLs) and defended in ORM (`create/write/unlink` restricted; closed membership rows immutable).
- Story/Task link cannot be moved across project/company while linked; task-derived fields are access-safe (no sudo escalation disclosure).
- Carry-over preserves source sprint history and is forbidden from closed/cancelled sources.
- Public action methods keep manager authorization checks; no client-forgeable context flag is used as a security boundary.

## 5. Deferred items / residual risks

- Concurrency stress tests for simultaneous closure, carry-over, and same-day events were not added.
- No DB-level terminal-state constraint for sprint `state` and no DB-level single-open-membership constraint (ORM + locks used).
- Re-entry to the same sprint after removal is now rejected (stricter than original behavior) to preserve history; alternative append-new-row schema would require constraint redesign.
- i18n `.po/.pot` files were not regenerated in this environment; no user-facing string keys removed but some messages changed/added — translation update required.
- Arabic RTL visual review not performed.

## 6. Files changed (remediation)

- `addons/amnus/amnus_agile/models/amnus_agile_sprint.py`
- `addons/amnus/amnus_agile/models/amnus_agile_user_story.py`
- `addons/amnus/amnus_agile/models/amnus_agile_membership.py`
- `addons/amnus/amnus_agile/models/amnus_agile_burndown.py`
- `addons/amnus/amnus_agile/models/amnus_agile_epic.py`
- `addons/amnus/amnus_agile/security/amnus_agile_security.xml`
- `addons/amnus/amnus_agile/tests/__init__.py`
- `addons/amnus/amnus_agile/tests/test_remediation.py` (new)
- `addons/amnus/amnus_projects/models/project_task.py`
- `docs/sprints/SPRINT_04_2_REMEDIATION.md` (this report)
- `docs/technical/amnus_agile.md` (updated)
- `docs/sprints/SPRINT_04.md` (updated)
- `CHANGELOG.md` (updated)

`docs/sprints/SPRINT_04_1_AUDIT.md` preserved unchanged.
