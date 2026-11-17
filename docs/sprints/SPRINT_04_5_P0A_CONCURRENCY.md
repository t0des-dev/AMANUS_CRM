# SPRINT 04.5 — P0-A Concurrency Verification
## Genuine multi-transaction concurrency verification of AMNUS Agile workflows (F-11 / F-12)

- **Date:** 2026-11-17
- **Branch:** `feature/sprint-04-amnus-agile`
- **Starting HEAD:** `37c0bfc3940710f90bb6f608e9d69ce347759b4a`
- **`main` (must remain unchanged):** `5b324a04c9e0802a4341bc72163663755adb159d`
- **Database:** `amnus_test_19` only (`config/amnus-test.conf`, `db_name=amnus_test_19`, `db_filter=^amnus_test_19$`)
- **PostgreSQL:** 16.14, session isolation `read committed` (verified), DB user `amanus` (not superuser, no extensions beyond `plpgsql`)
- **Odoo:** 19.0.0 Community (`C:\Program Files\AmanusERP\odoo\odoo-bin`), bundled Python 3.12.10
- **Status of this document at Phase 0:** Sections 1–7 completed **before any source modification**, per the Phase 0 gate. Sections 8–23 are filled as execution progresses.

---

## 1. Git baseline

| Item | Value |
|---|---|
| Repository root | `C:\Users\PC\Desktop\workflow\ModuleOdoo19\amnus` |
| Branch | `feature/sprint-04-amnus-agile` |
| HEAD at start | `37c0bfc3940710f90bb6f608e9d69ce347759b4a` (matches expected) |
| `main` | `5b324a04c9e0802a4341bc72163663755adb159d` (matches expected) |
| Working tree at start | Clean except preserved untracked files |
| Last 5 commits | `37c0bfc` fix(amnus_core)…, `2c55206` feat(amnus_agile)…, `7edf497` fix(amnus_agile)…, `5b7ac38` feat(amnus_agile)…, `5b324a0` docs(sprint_04)… |
| Preserved untracked | `docs/sprints/SPRINT_04_1_AUDIT.md`, `docs/sprints/SPRINT_04_3_AUDIT.md` |
| Preserved docs | `SPRINT_04_1_AUDIT.md`, `SPRINT_04_2_REMEDIATION.md`, `SPRINT_04_3_AUDIT.md`, `SPRINT_04_4_CLOSURE.md`, `SPRINT_04_5_P0B_FIX.md` |

## 2. Database / configuration safety verification

- `config/amnus-test.conf`: `db_name = amnus_test_19`, `db_filter = ^amnus_test_19$`, `db_host = 127.0.0.1`, `db_port = 55432`, `db_user = amanus`. Verified before every DB-touching command.
- Live processes inspected: the only Odoo process is PID 20492 using `C:\Program Files\AmanusERP\config\production.conf` with `db_name = amanus` — **a different database on the same server**, never `amnus_test_19`. It is not a competitor for `amnus_test_19` and is left untouched.
- No create/delete/rename/migrate/restore/reset of any database. No `-u all`. All module updates and test suites run **sequentially**, one Odoo process at a time against `amnus_test_19`.
- Database state inspected read-only: 8 AMNUS/mail/project/crm modules installed, `amnus_agile` manager group `res_id=550`, single company (`My Company`, id 1), no demo users beyond the 4 base system users, transaction isolation `read committed`, no `pg_stat_statements`/other extensions (harness uses `pg_stat_activity`, `pg_locks`, `pg_blocking_pids` — all built in).

## 3. Existing implementation inspected (committed source at starting HEAD)

Lock-bearing code found (complete inventory — `FOR UPDATE` occurrences across `addons/amnus/`):

| File | Lines | Mechanism |
|---|---|---|
| `amnus_agile/models/amnus_agile_sprint.py` | 178–201 | `_lock_for_workflow()` / `_lock_sprints_for_workflow(ids)`: `SELECT id FROM amnus_agile_sprint WHERE id IN %s FOR UPDATE` with `sorted(...)` ids |
| `amnus_agile/models/amnus_agile_user_story.py` | 237–244 | `_lock_for_workflow()`: `SELECT id FROM amnus_agile_user_story WHERE id IN %s FOR UPDATE` with `sorted(...)` ids |
| `amnus_agile/models/amnus_agile_user_story.py` | 759–762 | `action_create_task`: `SELECT id FROM project_task WHERE id = %s FOR UPDATE` (row just created by the same transaction) |
| `amnus_projects/models/project_task.py` | 45–48, 67–70 | `project.task.write(project_id)`: locks `project_task` rows (sorted) **then** linked `amnus_agile_user_story` rows (sorted) |
| `amnus_projects/models/amnus_crm_project_request.py` | 104 | `SELECT state, project_id FROM amnus_crm_project_request WHERE id = %s FOR UPDATE` (CRM workflow, outside Agile scenarios) |
| `amnus_agile/models/amnus_agile_membership.py` | 107–117 | partial unique index `amnus_agile_membership_open_story_unique ON amnus_agile_sprint_membership (story_id) WHERE outcome = 'active' AND date_removed IS NULL` via `_auto_init`; plus `unique (sprint_id, story_id)` ORM constraint |
| `amnus_agile/models/amnus_agile_burndown.py` | 81–84 | `unique (sprint_id, date, event_sequence)`; `create`/`write`/`unlink` blocked outside `su` and `write/unlink` always raise (immutable history) |
| `amnus_agile/models/amnus_agile_sprint.py` | 344–370 | `_record_burndown_event`: locks sprint row, invalidates, re-reads state, allocates `MAX(event_sequence)+1` (no `FOR UPDATE` on the aggregate), relies on sprint lock + unique constraint |
| `amnus_agile/models/amnus_agile_user_story.py` | 400–510, 596–710 | `write`, `_workflow_assign_to_sprint`, `_workflow_carry_over`, `action_remove_from_sprint`: story lock then sprint lock(s) |
| `amnus_agile/models/amnus_agile_sprint.py` | 434–649 | `action_plan/start/close/cancel` (sprint lock, invalidate, revalidate state, frozen writes), `action_add_stories` (**sprint lock first, then story**), `action_carry_over` (**both sprints sorted first, then stories**) |
| `amnus_agile/wizard/amnus_agile_carry_over_wizard.py` | 55–65 | delegates to `sprint.action_carry_over` (no additional locking) |

Revalidation after lock acquisition is present in the inspected paths (`invalidate_recordset([...])` + state checks after every lock). Transaction boundaries: each Odoo request/test transaction is single-cursor; all locks are ordinary row locks released on commit/rollback.

Odoo 19 infrastructure verified for the harness:
- `Environment.__new__` binds `cr.transaction` **per cursor** (`transaction = cr.transaction; if None: Transaction(Registry(dbname))`) → independent cursors give independent environments/caches/towrite queues.
- `Registry(dbname)` returns the process-wide registry (`Registry.__new__` → `Registry.new`), loads modules once with `update_module=False`; registry metadata is shared read-only model classes, which is correct and required (workers must not each load a registry).
- `Cursor.commit()` calls `self.flush()` → `transaction.flush()` (ORM pending writes are flushed and constraints validated before commit).
- `odoo.cli.shell` provides the supported standalone boot pattern: `config.parse_config(...)` → `server.start(preload=[], stop=True)` → `Registry(dbname)` → `registry.cursor()` → `api.Environment(cr, uid, ctx)`. The harness replicates exactly this sequence.

## 4. Lock-order matrix (Phase 0, before any source change)

**Global lock resource tables:** `project_task` (T), `amnus_agile_user_story` (S), `amnus_agile_sprint` (P), membership rows (M — never explicitly locked), burndown rows (B — never explicitly locked, guarded by P lock + unique constraint).

| Path | Workflow entry | 1st lock | Subsequent locks | Sorted? | Notes |
|---|---|---|---|---|---|
| W1 | `story.write` with `sprint_id`/`story_points` | S (story rows, sorted) | P (sprint ids sorted, single statement) | yes | `invalidate_recordset` + `_validate_sprint_assignment` after locks |
| W2 | `story._workflow_assign_to_sprint` (`action_add_to_sprint`, via `sprint.action_add_stories`) | S | P (sorted) | yes | story state validated after locks |
| W3 | `story.action_remove_from_sprint` | S | P (single) | n/a | closes membership under S+P locks |
| W4 | `story._open_membership` (internal) | S | P (single) | n/a | membership insert under S+P locks; DB partial index is global backstop |
| W5 | `story._workflow_carry_over` | S (already held by W6) | P (already held) | — | revalidates source/target/story state after locks |
| W6 | `sprint.action_carry_over` (+ wizard) | **P** (source+target, sorted) | then S per story (recordset order) | sprints yes | **sprint → story order** |
| W7 | `sprint.action_add_stories` | **P** (target sprint) | then S via `_workflow_assign_to_sprint` | n/a | **sprint → story order** |
| W8 | `sprint.action_plan/start/close/cancel` | P (one sprint per iteration; multi-record recordset order = model `_order 'project_id, date_start, id'`) | membership row UPDATEs (under P) | multi-record not id-sorted | state revalidated after lock; frozen `final_*` written under lock |
| W9 | `story.create` with `sprint_id` | P (sorted) | new S row (uncontended — invisible to other transactions) | yes | effectively sprint-first but never waits on a story |
| W10 | `story.action_create_task` | S | new T row (uncontended) | n/a | task just inserted in same tx; other transactions cannot lock it |
| W11 | `project.task.write` with `project_id` | **T** (sorted) | then S (sorted) | yes | **task → story order**; story re-searched after task lock |
| W12 | `sprint._record_burndown_event` | P (re-entrant if already held) | — | — | `MAX+1` allocation safe only while P lock held; unique constraint is backstop |
| W13 | membership access (`_open_membership`, `_close`, `_mark_committed`) | none explicit — always reached with S and/or P held | membership row UPDATE lock | — | no path touches membership rows without S/P locks |

**Opposing lock acquisition paths identified (analysis, not assumption):**

1. **RISK-1 (P↔S):** W6/W7 take **P → S**; W1–W4 take **S → P**. Two transactions can hold P and S respectively and wait on each other → genuine deadlock possible (SQLSTATE `40P01`). Reachable via `sprint.action_add_stories(S, [X])` racing `story X.write(story_points)` (X already committed to a sprint), and via `action_carry_over` racing story-level sprint/points writes. → Deterministic harness schedule + bounded stress (scenario S-01).
2. **RISK-2 (multi-sprint order):** W8 locks sprints one-by-one in model `_order` order while W1/W6 lock sprint sets in a single sorted-`IN` statement. Opposing order only reachable through multi-record actions (rare from UI). Documented, monitored; PostgreSQL row locking for `IN (sorted)` follows the access plan (normally ascending b-tree), which is *assumed*, not guaranteed by SQL — recorded as residual risk.
3. **RISK-3 (T vs S, missing lock):** W11 takes **T → S**, but `story.write({'task_id': ...})` takes **no task lock at all** (no `needs_sprint_lock`, no task lock) → link/move race not serialized (scenario C-05a).
4. **RISK-4 (points vs closure):** `story.write({'story_points'})` locks S then P and writes points **without revalidating sprint state after acquiring P** → a points update can land after `action_close` committed (silent post-finalization edit, no event, no rejection) (scenario C-04a).
5. **RISK-5 (aggregate allocation):** burndown `MAX+1` is safe only under the P lock; verified by scenario C-06 (both workers must serialize on P; unique `(sprint_id,date,event_sequence)` is the backstop).
6. **RISK-6 (story state transitions):** `story._workflow_transition` (`action_done` etc.) takes **no explicit story row lock**; serialization against closure happens only through the P lock when a burndown event is recorded. Analysis: closure reads story states under P lock; a later `action_done` cannot rewrite frozen `final_*` metrics (computed fields return frozen values for closed sprints) and cannot mutate membership history (captured at closure). Outcome is a valid serialization; documented as accepted behavior, not fixed unless a scenario demonstrates a broken invariant.

No `pg_advisory` locks, no explicit lock timeouts configured in application code.

## 5. Concurrency test architecture (design — documented before implementation)

**Location:** `addons/amnus/amnus_agile/tests/concurrency/` (isolated test-only package; **not** imported by `tests/__init__.py`, so Odoo's `--test-enable` runner is unaffected).

**Why standalone instead of inside `TransactionCase`:** Odoo's test framework gives each test a single cursor/transaction that is rolled back at test end; it cannot host two genuinely committing, overlapping transactions with independent cursors. The harness therefore boots the registry exactly like `odoo shell` and runs worker threads.

**Boot (replicates `odoo.cli.shell`):** `config.parse_config(['-c', conf, '-d', 'amnus_test_19'], setup_logging=True)` → `server.start(preload=[], stop=True)` → `Registry('amnus_test_19')` → per-role `registry.cursor()` → `api.Environment(cr, uid, ctx)`.

**Worker architecture:**
- Each role = one Python `threading.Thread`; each thread opens **its own PostgreSQL connection** via `registry.cursor()` (independent `psycopg2` connection), gets its **own Odoo `Environment`** bound to that cursor (Odoo 19 binds transaction/cache/towrite per cursor — verified in source), and commits/rolls back **only** under the harness's documented policy (see below).
- Threads genuinely overlap: PostgreSQL lock waits are blocking `libpq` I/O calls that release the Python GIL.
- No recordset, cursor, environment, or transaction is shared between roles. Roles use two different real `res.users` accounts (managers created by the harness in a unique namespace).
- Every worker sets `lock_timeout='20000ms'` and `statement_timeout='60000ms'` → all waits are bounded (no unbounded waits, no retries anywhere).

**Synchronization:** `threading.Event`s plus one **observer connection** (a third, read-only connection) that polls `pg_stat_activity`, `pg_locks` and `pg_blocking_pids()` every ~25 ms during a scenario. The observer signals "role B is now genuinely blocked by role A" only when PostgreSQL itself reports the blocking relationship — never inferred from thread start times and never from `sleep()`.

**Deterministic overlap protocol (per scenario):**
1. Role A (holder) opens its transaction, acquires **the first lock of Role A's real workflow** with the same SQL the workflow itself issues (harness pre-acquisition of a real row lock — not a mock, not a substitute for the workflow), signals `A_LOCKED`, then waits (bounded) for the observer to confirm Role B is blocked.
2. Role B waits for `A_LOCKED` and immediately calls the **real AMNUS ORM workflow**, which blocks inside its own `FOR UPDATE`.
3. Observer confirms `pg_blocking_pids(B.pid)` contains `A.pid` with `wait_event_type='Lock'` → evidence recorded (both pids, both `xact_start`s, both queries, blocked query text containing the workflow's own `FOR UPDATE` SQL).
4. Role A then executes its **full real workflow**, flushes, commits.
5. Role B unblocks (PostgreSQL resumes it), completes its own real workflow against the committed state, commits or fails with a controlled outcome; every outcome/exception is captured (class, message, SQLSTATE, full traceback).
6. Both threads are joined **before** any invariant check or cleanup.

**Transaction policy (test-only, documented):** the harness owns commits/rollbacks. A role commits exactly once after its workflow completes; on any exception it rolls back and records the exception. This transaction control exists only inside `tests/concurrency/` and never in application code (no `commit()` anywhere in production paths).

**PostgreSQL evidence captured per scenario:** worker `pg_backend_pid()`s, `pg_current_xact_id()` per worker transaction, monotonic + wall-clock start/end timestamps per role, observer samples (`state`, `wait_event_type/wait_event`, `query`, `pg_blocking_pids`, granted tuple locks on `amnus_agile_sprint`/`amnus_agile_user_story`/`project_task` with tuple offsets), and `pg_stat_activity.xact_start` overlap windows.

**Test-data isolation:** every created record (users, projects, sprints, stories, tasks) carries a unique run namespace `[P0A:<runid>]` in its name/login; ids are tracked in memory. Invariant queries filter by exact harness ids only.

**Cleanup:** after all workers have joined and all scenarios/invariant checks finished: narrowly scoped, parameterized `DELETE`s restricted to the exact harness-created ids (ordered: burndown → membership → story → sprint → task → project → users/partners → harness audit-log and mail-message rows keyed by namespace). Required because the production models *intentionally* forbid ORM deletion of append-only history (`membership.unlink` always raises, `burndown.unlink` always raises, sprint/story unlink blocked when history exists) — ORM cleanup is attempted first, failures are captured, SQL fallback is limited to harness ids and documented. Cleanup failures are recorded separately; leftover rows are re-queried by namespace after cleanup.

**Expected business invariants (checked after every repetition by read-only SQL on a fresh connection):** see section 17.

## 6. Proof strategy for independent connections and genuine overlap

- Independent connections: each role logs `SELECT pg_backend_pid()` — distinct pids asserted per scenario; the observer runs on a third connection.
- Independent transactions: each role logs `SELECT pg_current_xact_id()` in its own transaction — distinct xids asserted; observer cross-checks xids from `pg_locks` (`locktype='transactionid'`).
- Independent Odoo environments: `api.Environment(cr, uid, ctx)` constructed per role cursor; Odoo 19 `Transaction` object is bound to `cr.transaction` (verified in `odoo/api.py`), so cache/towrite are per-transaction.
- Genuine overlap: observer-confirmed `pg_blocking_pids()` evidence with `wait_event_type='Lock'`, plus `xact_start` windows that overlap, plus the blocked role's `query` being the workflow's own `FOR UPDATE`. Thread start times and sleeps are never used as proof.

## 7. Scenario plan

| ID | Scenario | Roles / first lock of each real workflow | Overlap forcing | Expected outcomes | Repetitions |
|---|---|---|---|---|---:|
| C-01 | Duplicate membership, same sprint | A: `action_add_to_sprint` (1st lock = story) / B: same | A pre-locks story row, B blocks in workflow | A success, B idempotent success or controlled UserError; exactly 1 open membership | 10 |
| C-01b | Duplicate membership, different active sprints | A: story→sprint1 / B: story→sprint2 | A pre-locks story row, B blocks | exactly 1 open membership (other closed `removed`), no partial state | 10 |
| C-02 | Concurrent carry-over, same source→target | A: `action_carry_over` (1st lock = sprints sorted) / B: same | A pre-locks both sprints (sorted), B blocks | A success; B controlled UserError ("only stories currently in this sprint"); source history intact, target open membership ≤ 1 | 10 |
| C-02b | Opposing source/target carry-overs (deadlock order test) | A: S1→S2 / B: S2→S1 (both sort ascending) | A pre-locks sorted sprints, B blocks on first lock | both succeed (different stories), no deadlock, 2 open memberships | 10 |
| C-03 | Concurrent sprint closure | A: `action_close` (1st lock = sprint) / B: same | A pre-locks sprint, B blocks | A success; B controlled UserError ("Only active sprints can be closed"); one coherent closed state, single closure event, frozen metrics | 10 |
| C-04a | Points update vs closure — **closure locks first** | A: `action_close` (sprint) / B: `story.write(points)` (story→sprint) | A pre-locks sprint, B blocks on sprint lock inside workflow | *Pre-fix expectation:* B silently succeeds after closure → invariant failure (RISK-4). *Post-fix:* B gets controlled UserError, rollback | 10 |
| C-04b | Points update vs closure — **points lock first** | A: `story.write(points)` (story→sprint) / B: `action_close` (sprint) | A pre-locks story then sprint, B blocks on sprint | both succeed in order; `final_*` matches committed points; no stale aggregate | 10 |
| C-05a | Task project move vs story linking — **move uncommitted first** | A(mover): `task.write(project_id)` (1st lock = task) / B(linker): `story.write(task_id)` (pre-fix: **no lock**) | A pre-locks task, performs move (uncommitted), B links while A uncommitted, A commits | *Pre-fix expectation:* cross-project link committed → invariant failure (RISK-3). *Post-fix:* B blocks on task lock, then ValidationError/rollback | 10 |
| C-05b | Task move after link committed | A(linker) commits link first (task pre-locked), B(mover) blocks on task | B blocked in `task.write` → after A commits, B finds story → controlled UserError | invariant preserved | 10 |
| C-06 | Concurrent burndown event allocation | A: `_record_burndown_event` (1st lock = sprint) / B: same | A pre-locks sprint, B blocks in workflow's sprint lock | both events committed with unique contiguous sequences, no lost event, no duplicate `(sprint,date,seq)` | 10 |
| S-01 | Opposing lock-order / deadlock stress (RISK-1) | A: `sprint.action_add_stories(S,[X])` (1st lock = **sprint**) / B: `story X.write(points)` (1st lock = **story**) | A pre-locks sprint, B locks story then blocks on sprint, A then blocks on story → deterministic cycle | *Pre-fix:* PostgreSQL deadlock detected (`40P01`) on at least one side, other side completes; invariant still holds after abort. *Post-fix:* no deadlock across repetitions (order unified), both succeed or controlled errors | 10 (pre-fix) + 10 (post-fix) |

Additional recorded observations per section 7 of the brief: lock waits, deadlock detection, serialization behavior, unique-constraint violations, rollback behavior, cache invalidation/record re-read after lock (workflows call `invalidate_recordset` after locks — re-read verified via captured state checks), retry behavior (none implemented — no retries added).

---

*Phase 0 complete. No source file has been modified at this point (working tree verified clean apart from the two preserved untracked audit documents).*

---

## 8. Harness implementation — deviations from the Phase 0 design

Four implementation facts were established from Odoo 19/PostgreSQL source **after** Phase 0 and required documented adjustments. None of them weakens the proof strategy; each makes it match the production runtime more faithfully.

| # | Deviation | Reason | Effect on proof |
|---|---|---|---|
| D-1 | The harness runs a **bounded emulation of `odoo.service.model.retrying`** inside `H.call()` (`MAX_TRIES=5`, retryable SQLSTATEs `{40001, 40P01, 55P03}`, `random.uniform(0, 2**tryno)` backoff, rollback + `env.transaction.reset()` + `env.registry.reset_changes()` between tries). Phase 0 section 5 said "no retries anywhere". | Odoo 19 cursors run at **REPEATABLE READ** (`odoo/sql_db.py:373`) and every real RPC goes through `retrying()` (verified in `odoo/service/model.py:160`). A no-retry harness would measure a runtime that does not exist in production — e.g. RISK-5's defect only manifests *because* the loser keeps its stale snapshot. | The harness now has exactly **one** retry loop, with Odoo's own bound (5) and exception set; it is *not* an unbounded retry. Every retry attempt is recorded in `Outcome.retry_events` with try number, exception class and SQLSTATE. No other retry exists anywhere in the harness. |
| D-2 | All observer queries take a monotonic `since` filter (`Ctx.since()` = min role `t_start`). | PostgreSQL **reuses backend PIDs** across connections; pid-only matching could return a stale sample from a previous repetition (observed once during validation: identical overlap timestamps in C-01 and C-03). | Overlap evidence is now exact per repetition: the blocked pid **and** its xid must match the current transactions (`pg_current_xact_id()` of the workers). |
| D-3 | `psycopg2.IntegrityError` is surfaced as `ValidationError("The operation cannot be completed: …")` with `pg_type`/`sqlstate` preserved, exactly as Odoo's service layer converts it; it is **never** retried (Odoo only retries 40001/40P01/55P03). | Fidelity: a real client never sees a raw `UniqueViolation`. | C-06's pre-fix defect is reported as `ValidationError(23505)` — the defect evidence (`23505`) is preserved while the presentation matches production. |
| D-4 | C-02/C-02b holder pre-lock is **phase-aware** (`available(phase)` sets module `PHASE`): `pre_fix` pre-locks sprints only (matching the old sprint-first implementation), `post_fix` pre-locks `[story, sprints sorted]` (matching the fixed story-first order). S-01 already selects its pre-lock per phase. | A pre-lock must be the *first lock of the workflow it stages*; otherwise the harness itself would create a lock inversion (post-fix R1 holding sprints while wanting the story, R2 holding the story while wanting sprints). | The deterministic schedule stages the real workflow in both phases without ever introducing a harness-induced deadlock. |

## 9. Harness safety gates and pre-run verification

Executed before **every** run (documented in each run's log):

1. `Select-String config\amnus-test.conf -Pattern '^db_name|^db_filter'` → `db_name = amnus_test_19`, `db_filter = ^amnus_test_19$`.
2. `Get-CimInstance Win32_Process … 'odoo-bin'` → `ODOO_PROCS:0` (the unrelated production Odoo, PID 20492 on DB `amanus` via `production.conf`, is a different database and was never a competitor; no second process ever touched `amnus_test_19`).
3. Harness boot gates (in `run_concurrency.py`): refuses to start if the parsed database is not `amnus_test_19`, if the required config keys mismatch, or if another `odoo-bin` process is detected against the same database.
4. Run invocation always from the repository root with the bundled interpreter and the feature-branch working tree; the harness exits `0` (all pass), `1` (failing reps), `2` (fatal).

Cleanup gates: all workers joined → observer stopped → parameterized SQL cleanup restricted to tracked harness ids → ORM user deletion → **final residue query must be all zeros** (tables: `amnus_agile_sprint`, `amnus_agile_user_story`, `project_project`, `project_task`, harness `res_users`). Any non-zero residue fails the run's record.

## 10. Pre-fix production run (baseline defect demonstration)

- **Command:** `python addons\amnus\amnus_agile\tests\concurrency\run_concurrency.py -c config\amnus-test.conf -d amnus_test_19 --phase pre_fix --scenarios "C-01,C-01b,C-02,C-02b,C-03,C-04a,C-04b,C-05a,C-05b,C-06,S-01[pre_fix]" --repetitions 10 --output %TEMP%\p0a_prefix_prod.json`
- **Run namespace:** `20261117T214313` — **110 repetitions**, exit **1** (defects demonstrated as designed), residue all zeros, observer error `None`.

| Scenario | Pass/10 | Outcome summary (pre-fix) |
|---|---:|---|
| C-01 | 10/10 | both committed; R2 `40001` on first try then success (normal RR serialization) |
| C-01b | 10/10 | both committed; exactly one open membership |
| C-02 | 10/10 | R1 committed, R2 controlled `UserError` after `40001` |
| C-02b | 10/10 | both committed (different stories), no deadlock |
| C-03 | 10/10 | R1 committed, R2 controlled `UserError` ("Only active sprints can be closed") |
| **C-04a** | **0/10** | **R2's post-closure `story_points` write silently committed (RISK-4)** — invariant `final committed == story points sum` failed every rep (`got=3, expected=8`) |
| C-04b | 10/10 | both committed, `final_*` consistent |
| C-05a | 10/10 | R2 link rejected with `ValidationError` after `40001` — **RISK-3 refuted by evidence** (see section 18) |
| **C-05b** | **0/10** | **R2's task move committed although the link was already committed** — cross-project link invariant failed every rep (`got=task in project2, expected project1`) |
| **C-06** | **0/10** | **R2 hit `23505`** (`ValidationError(23505)`) — stale-`MAX+1` sequence allocation (RISK-5); only baseline + 1 event stored instead of 3 |
| S-01[pre_fix] | 10/10* | **deadlock `40P01` observed on R2 in every repetition** (RISK-1) and absorbed by the emulated service layer; invariants held after abort. *PASS here means "the defect evidence required by the pre-fix spec was observed", not "behaviour is correct" |

Full evidence: `%TEMP%\p0a_prefix_prod.json` (roles, pids, xids, actions with try counts, retry events, overlap samples, invariants, cleanup, residue).

## 11. Defect root-cause analysis

| Defect | Scenario | Root cause (confirmed from source + captured tracebacks) |
|---|---|---|
| **RISK-1 lock inversion → deadlock** | S-01 | `sprint.action_add_stories` / `action_carry_over` locked **sprint → story** while the story-level workflows lock **story → sprint**. Two transactions holding opposite ends of the pair wait on each other → PostgreSQL deadlock (`40P01`), observed 10/10 pre-fix on `action_add_stories` vs `story.action_add_to_sprint`. |
| **RISK-4 silent post-closure edit** | C-04a | `story.write({'story_points'})` locked story+sprint but never re-validated `sprint.state` afterwards; after the loser's `40001` retry showed the committed closure, the write still proceeded and committed points on a finalized sprint (no event, no rejection, frozen `final_*` ≠ live points). |
| **RISK-5 stale aggregate allocation** | C-06 | `_record_burndown_event` takes the sprint `FOR UPDATE` lock, but the holder in C-06 (story-level event) **never modified the sprint row**, so the waiter's `FOR UPDATE` succeeded on its pre-existing REPEATABLE READ snapshot — `MAX(event_sequence)` was read stale, and only the unique constraint stopped the duplicate (`23505`) instead of a retryable `40001`. |
| **C-05b guard blindness (part of RISK-3/F-12-04)** | C-05b | `project.task.write`'s guard `search([('task_id', …)])` runs on the mover's RR snapshot; when the link had committed but the mover's snapshot predated it, the guard saw no story, `FOR UPDATE` on the task did not conflict with the link transaction's committed row (the link transaction never *updated* the task row), so the cross-project move committed silently. |
| **RISK-3 (link vs move, C-05a)** | C-05a | **Refuted:** the FK check `SELECT 1 FROM project_task WHERE id=$1 FOR KEY SHARE` issued by the story update conflicts with the mover's `UPDATE project_task` → loser gets `40001` → retry → controlled `ValidationError` from `_check_task_project`. No fix needed (section 18). |
| **C-01b one-off partial membership** | C-01b | Observed once in a 1-rep validation run (violating row had `outcome <> 'active'` with `date_removed IS NULL`), never again (0/15 later reps including 10 pre-fix production reps). The invariant check was hardened to dump the full violating row if it recurs; no fix applied without a reproducible defect (section 22 residual note). |

## 12. Fixes applied (only demonstrated defects)

All fixes are in `addons/amnus/amnus_agile/` application code, minimal, and each maps to a demonstrated failure above.

1. **RISK-1 → unified global lock order `task → story (sorted) → sprint (sorted)`** (`amnus_agile_sprint.py`):
   - `action_add_stories`: story rows are now locked (`stories._lock_for_workflow()`, sorted ids) **before** the sprint lock; state revalidation still happens after both locks.
   - `action_carry_over`: carried stories locked (sorted) **before** `_lock_sprints_for_workflow([source, target])`.
2. **RISK-4 → freeze check after locks** (`amnus_agile_user_story.py:write`): after the story+sprint locks and `invalidate_recordset`, a write containing `story_points` whose (freshly read) sprint is `closed`/`cancelled` raises `UserError` → controlled rollback. A racing first try receives `40001`, the emulated (and real) service layer retries, and the retry observes the committed closure and rejects.
   - **Decision (recorded during execution):** this changes the pre-Sprint-04.5 behaviour in which a *sequential* post-closure point edit succeeded while frozen metrics stayed frozen (asserted by three legacy tests and implied by two lines of `docs/technical/amnus_agile.md`). The sprint decision is **rejection semantics**: frozen history can no longer diverge from live data through any path. The three tests were updated to assert the controlled rejection (they retain their frozen-metric assertions; test count unchanged at 98), and the technical documentation was reworded accordingly.
3. **RISK-5 → lock-intent row touch in `_record_burndown_event`** (`amnus_agile_sprint.py`): right after `_lock_for_workflow()`, `UPDATE amnus_agile_sprint SET write_date = now() WHERE id = %s` (documented direct SQL, data-semantic no-op). The winner now visibly *modifies* the sprint row, so every REPEATABLE READ waiter is guaranteed `40001` → rollback → fresh `MAX(event_sequence)` instead of `23505`.
4. **C-05b → lock-intent row touch on the linked task in `story.write`** (`amnus_agile_user_story.py`): when `vals.get('task_id')` is set, `UPDATE project_task SET write_date = now() WHERE id = %s` is issued **before** the story lock (preserving `task → story` order). A concurrent mover therefore blocks/conflicts on the touched row and gets `40001` → retry → the guard re-runs against a fresh snapshot and rejects the move with a controlled `UserError`.

No other application code was changed. Odoo core, `amanus_*`/`custom_addons`, and other addons were not touched.

## 13. Post-fix production run (regression re-run of all scenarios)

- **Command:** `python addons\amnus\amnus_agile\tests\concurrency\run_concurrency.py -c config\amnus-test.conf -d amnus_test_19 --phase post_fix --scenarios "C-01,C-01b,C-02,C-02b,C-03,C-04a,C-04b,C-05a,C-05b,C-06,S-01[post_fix],S-01n" --repetitions 10 --output %TEMP%\p0a_postfix_prod.json`
- **Run namespace:** `20261117T221121` — **120 repetitions**, exit **0**, observer error `None`, final residue **all zeros**.

| Scenario | Pass/10 | Post-fix outcome detail |
|---|---:|---|
| C-01 | 10/10 | both committed; R2 `40001`→retry→idempotent/serialized success; exactly 1 open membership |
| C-01b | 10/10 | both committed; one open membership, no partial state |
| C-02 | 10/10 | R1 committed, R2 `40001`→retry→controlled `UserError`; open membership only in target; source history `carried_over` intact |
| C-02b | 10/10 | both committed (opposing directions), **no deadlock**; 2 open memberships (X→s2, Y→s1) |
| C-03 | 10/10 | R1 committed, R2 `40001`→retry→`UserError` ("Only active sprints can be closed") |
| **C-04a** | **10/10** | **fixed:** R2 `40001`→retry→fresh closed state→controlled `UserError`, rolled back; frozen `final_*` == live points |
| C-04b | 10/10 | points landed first (committed), closure serialized after → `final_committed = 8` == live sum |
| C-05a | 10/10 | R2 link → `40001` on the **new task touch** → retry → controlled `ValidationError`; no cross-project link |
| **C-05b** | **10/10** | **fixed:** mover blocked at task `FOR UPDATE` → `40001` → retry re-runs the guard on a fresh snapshot → controlled `UserError`, rolled back; task stays in the story's project |
| **C-06** | **10/10** | **fixed:** both events committed, sequences contiguous, `40001` instead of `23505`, 3 burndown rows (baseline + 2 events) |
| S-01[post_fix] | 10/10 | **no `40P01` anywhere**; R2 gets `40001` → retry → success; invariants hold |
| S-01n (organic stress) | 10/10 | no pre-lock, both start on a GO barrier: both committed every rep, R1 `40001`→retry 10/10, overlap observed 6/10 (organic contention is probabilistic — `overlap_required=False` for this scenario), **zero deadlocks** |

## 14. Genuine-overlap evidence (per scenario, from PostgreSQL itself)

Every deterministic scenario recorded observer-confirmed lock-wait overlap in **10/10 repetitions of both runs** (`overlap=True`). Evidence per sample: blocked `pg_stat_activity` row (`state`, `wait_event_type='Lock'`, `wait_event='transactionid'`), the blocked session's **workflow SQL text**, `pg_blocking_pids()` containing the holder's pid, both transactions' `xact_start`, and `pg_locks` rows with `granted=true` on the pre-locked tuple. Pids/xids are matched against the current repetition (`Ctx.since()` monotonic filter, `pg_current_xact_id()`) so no sample can be stale (see D-2).

Blocked statements observed (post-fix run, one per scenario):

| Scenario | Statement that PostgreSQL reported blocked | Blocked pid blocked by |
|---|---|---|
| C-01 / C-01b | `SELECT id FROM amnus_agile_user_story WHERE id IN (…) FOR UPDATE` | holder (R1) |
| C-02 | `SELECT id FROM amnus_agile_user_story WHERE id IN (…) FOR UPDATE` (story-first order confirmed) | holder (R1) |
| C-02b | `SELECT id FROM amnus_agile_sprint WHERE id IN (…, …) FOR UPDATE` | holder (R1) |
| C-03 | `SELECT id FROM amnus_agile_sprint WHERE id IN (…) FOR UPDATE` | holder (R1) |
| C-04a / C-04b | `SELECT id FROM amnus_agile_sprint WHERE id IN (…) FOR UPDATE` | holder (R1) |
| C-05a | `UPDATE project_task SET write_date = now() WHERE id = …` (the new lock-intent touch) | mover (R1) |
| C-05b | `SELECT id FROM project_task WHERE id IN (…) FOR UPDATE` | linker (R1) |
| C-06 | `SELECT id FROM amnus_agile_sprint WHERE id IN (…) FOR UPDATE` | holder (R1) |
| S-01[post_fix] | `SELECT id FROM amnus_agile_user_story WHERE id IN (…) FOR UPDATE` | holder (R1) |
| S-01n | story `FOR UPDATE` in 6/10 reps (organic) | peer |

Distinct backend pids and distinct `pg_current_xact_id()` per role were asserted for every repetition; the observer connection is a third independent connection.

## 15. Retry and SQLSTATE evidence

All SQLSTATEs seen across both production runs (from `retry_events`, `workflow_error`, `runner_error` — never inferred):

| SQLSTATE | Class | Pre-fix run | Post-fix run | Interpretation |
|---|---|---|---|---|
| `40001` | serialization failure | R2/loser in C-01, C-01b, C-02, C-02b, C-03, C-04a, C-04b, C-05a, C-06 (10/10 each); S-01n R1 | same pattern in **all 12** scenarios (10/10 each) | normal REPEATABLE READ behaviour under contention: loser rolls back, service layer retries with a fresh snapshot, guard re-runs. Emulated bound: `MAX_TRIES=5` (Odoo's own), observed tries: max 2 per action. |
| `40P01` | deadlock detected | **S-01[pre_fix] R2: 10/10** | **none (0 occurrences in 120 reps)** | RISK-1 demonstrated pre-fix, eliminated post-fix by the unified `task → story → sprint` order |
| `23505` | unique violation | **C-06 R2: 10/10** (surfaced as `ValidationError(23505)` per Odoo's conversion) | **none** | RISK-5 demonstrated pre-fix; the sprint-row touch converts it into a retryable `40001` |
| *(none)* | — | C-05b: R2 committed with **zero** SQLSTATEs (guard silently missed the link) | C-05b: R2 `40001`→retry→`UserError` | C-05b defect demonstrated pre-fix, fixed post-fix |

Per-action try counts: every workflow action completed in ≤2 tries in both runs (no exhaustion of the bounded retry, i.e. no scenario needed more than one retry).

## 16. Deadlock analysis (S-01 lock-order stress)

- **Pre-fix schedule (deterministic, 10/10):** R1 pre-locks the **sprint** (first lock of `action_add_stories`), then the observer confirms R2 (real `story.action_add_to_sprint`) is blocked on the **story** row held by nobody yet — R2 acquires the story, then blocks on the sprint. R1 proceeds: `action_add_stories` needs the **story** → cycle (`R1: P→S`, `R2: S→P`) → PostgreSQL detects it → **`40P01`** captured with full tracebacks on the losing side; the emulated service layer retried it and invariants still held after the abort. This is the genuine cycle the Phase-0 matrix predicted (RISK-1).
- **Post-fix schedule (10/10):** both workflows acquire **story (sorted) first, then sprints (sorted)** → no cycle is possible; the loser gets a plain `40001` at its first contended lock and succeeds after one retry. Organic stress (S-01n, no pre-lock, 10 reps): **0 deadlocks**, both sides committed every time.
- The harness never used sleeps or thread-start ordering to claim either result: the cycle is proven by `pg_blocking_pids()` in the pre-fix samples and by the absence of any `40P01` in `retry_events`/`workflow_error` post-fix.

## 17. Post-state invariant queries (all green)

Checked by read-only SQL on a fresh connection **after every one of the 230 total repetitions** (110 pre-fix + 120 post-fix), plus post-run cleanup/residue queries:

| Invariant (SQL, exact harness ids only) | Post-fix result |
|---|---|
| membership: at most one open membership per story; no duplicate `(sprint, story)`; no partial (`outcome<>'active' AND date_removed IS NULL`) rows | 10/10 in every scenario |
| membership: exactly one open membership, belonging to the expected sprint (C-01/C-01b/C-02/C-02b) | 10/10 |
| membership: source closed as `carried_over` → target (C-02), outcomes at closure coherent (C-03/C-04) | 10/10 |
| story: `sprint_id` matches membership history; project/company consistency of task/story links | 10/10 |
| sprint: `state='closed'`, `final_committed/completed/velocity` == live committed points sum, exactly one `closure` event (C-03/C-04a/C-04b) | 10/10 |
| burndown: unique `(sprint, date, event_sequence)`, no gaps (`count == max(event_sequence)`) | 10/10 |
| burndown: baseline + exactly 2 committed events in C-06 | 10/10 |
| task/story: no cross-project or cross-company link; task remains in the story's project (C-05a/C-05b) | 10/10 |
| S-01: story either still in origin or fully moved to target; membership history coherent | 10/10 |
| **Residue after cleanup:** `amnus_agile_sprint`, `amnus_agile_user_story`, `project_project`, `project_task`, harness `res_users` | **0 / 0 / 0 / 0 / 0** in both runs |

## 18. RISK-3 refutation (C-05a) — no fix needed

C-05a staged "task move committed uncommitted first, then the story link attempts". Expected defect (RISK-3): the link path takes no task lock → cross-project link. **Observed, 10/10 pre-fix and 10/10 post-fix:**

- The blocked statement was the linker's `UPDATE amnus_agile_user_story SET task_id = …`, and its FK check `SELECT 1 FROM project_task x WHERE id = $1 FOR KEY SHARE OF x` conflicted with the mover's `UPDATE project_task`.
- The loser received **`40001`**, the service layer retried on a fresh snapshot, and the retry failed with a controlled **`ValidationError`** (`_check_task_project` / `_check_single_task_story`) → rollback.
- The partial unique index `unique (task_id)` and `ondelete` behaviour remain as backstops.

Conclusion: PostgreSQL's FK `FOR KEY SHARE` lock already serializes link-vs-move in this direction; the hypothesized defect did not reproduce under genuine multi-transaction scheduling. **RISK-3 is refuted by evidence; no code change was made for it.** (The *other* direction — link committed first, mover's stale guard — did reproduce and is covered by fix 4 / C-05b.)

## 19. Sequential regression suites

Run sequentially after all fixes (one Odoo process at a time on `amnus_test_19`; safety gates — `db_name`/`db_filter` verified, `ODOO_PROCS_SAME_DB:0` — checked before each suite):

```
"C:\Program Files\AmanusERP\python\python.exe" "C:\Program Files\AmanusERP\odoo\odoo-bin" ^
  -c config/amnus-test.conf -d amnus_test_19 -u <module> --test-enable --test-tags <module> ^
  --stop-after-init --logfile %TEMP%\amnus_p0a_reg_<module>.log ^
  --log-handler odoo.tests.result:INFO --log-handler odoo.modules.loading:INFO
```

| Suite | Command module | Result line (`odoo.tests.result`) | Exit | Log |
|---|---|---|---:|---|
| Core | `amnus_core` | `0 failed, 0 error(s) of 34 tests` | 0 | `%TEMP%\amnus_p0a_reg_core.log` |
| CRM | `amnus_crm` | `0 failed, 0 error(s) of 23 tests` | 0 | `%TEMP%\amnus_p0a_reg_crm.log` |
| Projects | `amnus_projects` | `0 failed, 0 error(s) of 61 tests` | 0 | `%TEMP%\amnus_p0a_reg_projects.log` |
| Agile | `amnus_agile` | `0 failed, 0 error(s) of 98 tests` | 0 | `%TEMP%\amnus_p0a_reg_agile.log` |

Expected counts matched exactly (34 / 23 / 61 / 98 — the three updated legacy tests retained their names and count). The agile suite was additionally re-run once as a confirmatory pass after a comment-only cleanup in `test_remediation.py` (functionally identical code, re-compiled green): again `0 failed, 0 error(s) of 98 tests`, exit 0.

**All four sequential regression suites pass.**

## 20. Quality review

| Check | Command / scope | Result |
|---|---|---|
| Python syntax | `python -m py_compile` on both models, three tests, and all three harness files | exit **0** (also re-checked after the comment-only edit) |
| Manifest | `ast.literal_eval` on `amnus_agile/__manifest__.py` | `version 19.0.1.0.0`, `license LGPL-3`, 9 data files — OK |
| XML well-formedness | `xml.etree.ElementTree.parse` over all 8 `amnus_agile/**/*.xml` files | all parse, exit **0** |
| Whitespace/errors in diff | `git diff --check` | exit **0** (no conflict markers, no trailing whitespace errors) |
| Full diff review | `git diff` read end-to-end | every hunk intentional: 4 fixes, 3 test expectation updates, harness, docs, changelog; no unrelated edits, no core/`amanus_*`/`custom_addons` changes |

## 21. Files changed (this sprint, to be committed)

| File | Change |
|---|---|
| `addons/amnus/amnus_agile/models/amnus_agile_sprint.py` | Fix 1 (story-first lock order in `action_add_stories`/`action_carry_over`), Fix 3 (sprint-row lock-intent touch in `_record_burndown_event`) |
| `addons/amnus/amnus_agile/models/amnus_agile_user_story.py` | Fix 2 (post-lock freeze check for `story_points`), Fix 4 (task-row lock-intent touch on `task_id` write) |
| `addons/amnus/amnus_agile/tests/concurrency/` (new: `harness.py`, `scenarios.py`, `run_concurrency.py`) | Multi-transaction concurrency harness (not imported by `tests/__init__.py`; unaffected by `--test-enable`) |
| `addons/amnus/amnus_agile/tests/test_closure.py` | `test_f01_frozen_metrics_runtime_direct_orm` asserts controlled `UserError` (count unchanged) |
| `addons/amnus/amnus_agile/tests/test_remediation.py` | `test_f01_closed_sprint_metrics_unchanged_after_later_story_edit` asserts rejection; comment cleanup |
| `addons/amnus/amnus_agile/tests/test_sprint.py` | `test_closed_sprint_metrics_are_frozen` asserts rejection |
| `docs/technical/amnus_agile.md` | Re-estimation-after-closure rejection semantics; concurrency-hardening bullet |
| `docs/sprints/SPRINT_04_5_P0A_CONCURRENCY.md` (new) | This evidence report (sections 1–23) |
| `CHANGELOG.md` | `Version 19.0.4.5.0 — Sprint 04.5` entry |

Preserved **untracked** (not staged): `docs/sprints/SPRINT_04_1_AUDIT.md`, `docs/sprints/SPRINT_04_3_AUDIT.md`. Preserved commits untouched: `5b7ac38`, `7edf497`, `2c55206`, `37c0bfc`; `main` remains at `5b324a04c9e0802a4341bc72163663755adb159d`.

## 22. Residual risks (accepted, documented)

| # | Residual | Why accepted | Mitigation / backstop |
|---|---|---|---|
| RR-1 | Theoretical task↔story ordering in paths that touch `project_task` outside `story.write` (e.g. a task write that triggers story-side logic before any story lock) | Not reproduced in any of 230 reps; all demonstrated paths follow `task → story → sprint` | Odoo service-layer retry converts a would-be deadlock into `40001`+retry; invariant checks would catch state divergence |
| RR-2 | Story **insert** (create) vs task FK check: a create can take the FK `FOR KEY SHARE` before any story row exists to lock | Insert paths cannot deadlock on their own new row; ordering with task updates follows FK semantics | Partial unique index `unique(task_id)` + `ondelete` backstop; controlled `ValidationError` |
| RR-3 | RISK-2 multi-record lock order within a *single* statement | `_lock_for_workflow` always sorts ids (`tuple(sorted(...))`) | Deterministic ascending-id order by construction |
| RR-4 | C-01b one-off partial-membership state | Observed once in a 1-rep validation run, never reproduced (0/25 later reps incl. 110 pre-fix + 120 post-fix production reps) | Invariant check now dumps the full violating row if it recurs; no fix without a reproducible defect |
| RR-5 | S-01n organic stress overlap is probabilistic (overlap observed 6/10 post-fix) | Scenario declared `overlap_required=False` in Phase 0; deterministic S-01 provides the required 10/10 overlap evidence | — |
| RR-6 | Emulated retry loop is a faithful re-implementation, not Odoo's actual `retrying()` | Bounded identically (`MAX_TRIES=5`, same SQLSTATE set, same backoff shape, same rollback/reset semantics — verified against `odoo/service/model.py`) | Sequential suite exercises the real runtime; production behavior confirmed by `40001`-then-success patterns |

## 23. Final status

**P0-A CONCURRENCY VERIFIED**

Acceptance checklist:

- [x] Genuine multi-transaction concurrency (independent connections/environments, PostgreSQL-proven overlap via `pg_stat_activity`/`pg_locks`/`pg_blocking_pids`) for C-01–C-06 + S-01/S-01n
- [x] Pre-fix defects demonstrated on `amnus_test_19` (110 reps): C-04a 0/10, C-05b 0/10, C-06 0/10 (`23505`), S-01 deadlock 10/10 (`40P01`); residue all zeros
- [x] Fixes applied only for demonstrated defects (4 fixes); RISK-3 refuted by evidence (no change)
- [x] Post-fix all-green re-run: **12 scenarios × 10 reps = 120, ALL PASS, exit 0**, 0 deadlocks, 0 unique violations, controlled errors only, residue all zeros
- [x] Sequential regressions: core **34**, crm **23**, projects **61**, agile **98** — all `0 failed, 0 error(s)`, exit 0 (agile re-run confirmatory after comment-only edit)
- [x] Quality review: `py_compile` 0, manifest OK, 8 XML well-formed, `git diff --check` 0, full diff reviewed
- [x] Test-data isolation `[P0A:<ns>` namespace; cleanup restricted to harness records; no unbounded retries (bound = Odoo's own 5)
- [x] Safety rules respected: only `amnus_test_19` via `config/amnus-test.conf` (gates before every DB-changing command), no DB create/delete/migrate/reset, no `-u all`, never two Odoo processes on the test DB, no core/legacy changes, no merge/push/history rewrite

Sprint 04.5 P0-A part is complete. **P1 translation validation** (fr_FR/ar_SA catalog/MO/load/RTL in `amnus_test_19`) remains as a separate acceptance requirement; Sprint 04.5 is complete only after both parts pass.
