# -*- coding: utf-8 -*-
"""Mandatory concurrency scenarios C-01..C-06 (+ S-01 lock-order stress).

Every scenario runs two worker roles, each in its own thread with its own
PostgreSQL connection and its own Odoo Environment (see ``harness``).  The
holder role pre-acquires *the first lock of its real workflow* (the same
``SELECT ... FOR UPDATE`` the workflow itself issues) so that the contender
role demonstrably blocks inside its own real ORM workflow; overlap proof always
comes from ``pg_stat_activity`` / ``pg_locks`` / ``pg_blocking_pids`` captured by
the independent observer connection.

Expectations encode the REQUIRED business behaviour.  A pre-fix run may fail an
expectation/invariant: that is the demonstrated defect, recorded as evidence.
"""
from __future__ import annotations

import harness as H

SYNC = H.SYNC_TIMEOUT

# ---------------------------------------------------------------------------
# Fixture helpers (sequential setup phase, superuser env, committed before the
# workers of the repetition start)
# ---------------------------------------------------------------------------


class Fixture:
    def __init__(self, env, ns: str, created: dict):
        self.env = env
        self.ns = ns
        self.created = created
        self._projects: dict[str, object] = {}

    def project(self, key: str):
        if key not in self._projects:
            rec = self.env["project.project"].create({
                "name": f"[P0A:{self.ns}] project {key}",
                "company_id": self.env.company.id,
            })
            self.created["projects"].append(rec.id)
            self._projects[key] = rec
        return self._projects[key]

    def sprint(self, key: str, project, start="2026-01-05", end="2026-01-18"):
        rec = self.env["amnus.agile.sprint"].create({
            "name": f"[P0A:{self.ns}] {key}",
            "project_id": project.id,
            "date_start": start,
            "date_end": end,
        })
        self.created["sprints"].append(rec.id)
        return rec

    def story(self, key: str, project, points=3, **vals):
        vals = {"name": f"[P0A:{self.ns}] {key}", "project_id": project.id,
                "story_points": points, **vals}
        rec = self.env["amnus.agile.user.story"].create(vals)
        self.created["stories"].append(rec.id)
        return rec

    def task(self, key: str, project):
        rec = self.env["project.task"].create({
            "name": f"[P0A:{self.ns}] {key}", "project_id": project.id,
        })
        self.created["tasks"].append(rec.id)
        return rec


def _plan(env, sprint):
    sprint.action_plan()


def _start(env, sprint):
    sprint.action_start()


# ---------------------------------------------------------------------------
# Shared role patterns
# ---------------------------------------------------------------------------


def holder_block_then_work(pairs_fn, wf_fn, note_key="OVERLAP"):
    """R1-style holder: prelock -> signal -> wait contender blocked -> workflow."""

    def role(ctx, env, cr, o):
        pairs = pairs_fn(ctx.ids)
        ctx.notes[f"{o.role}_PRELOCK"] = H.prelock(cr, pairs)
        ctx.sync.set(f"{o.role}_LOCKED")
        other = "R2" if o.role == "R1" else "R1"
        sample = ctx.observer.wait_blocked(ctx.role_pid(other), o.pid, SYNC,
                                           since=ctx.since())
        ctx.notes[note_key] = sample
        H.call(o, wf_fn.__name__, lambda: wf_fn(ctx, env),
               cr=cr, env=env, prelock_pairs=pairs)

    return role


def contender_wait_then_work(wf_fn):
    """R2-style contender: wait holder locked -> workflow (blocks inside)."""

    def role(ctx, env, cr, o):
        other = "R1" if o.role == "R2" else "R2"
        if not ctx.sync.wait(f"{other}_LOCKED", SYNC):
            raise TimeoutError(f"holder {other} never locked")
        H.call(o, wf_fn.__name__, lambda: wf_fn(ctx, env), cr=cr, env=env)

    return role


def natural_go_then_work(wf_fn):
    """No prelock: both roles start on a GO barrier (bounded organic stress)."""

    def role(ctx, env, cr, o):
        ctx.sync.set(f"{o.role}_READY")
        if not (ctx.sync.wait("R1_READY", SYNC) and ctx.sync.wait("R2_READY", SYNC)):
            raise TimeoutError("peer never ready")
        ctx.sync.set("GO")
        ctx.sync.wait("GO", SYNC)
        H.call(o, wf_fn.__name__, lambda: wf_fn(ctx, env), cr=cr, env=env)

    return role


# ---------------------------------------------------------------------------
# Workflow callables (real ORM entry points)
# ---------------------------------------------------------------------------


def wf_add_to_sprint(ctx, env):
    return env["amnus.agile.user.story"].browse(ctx.ids["story"]).action_add_to_sprint(
        ctx.ids["sprint"])


def wf_add_to_sprint2(ctx, env):
    return env["amnus.agile.user.story"].browse(ctx.ids["story"]).action_add_to_sprint(
        ctx.ids["sprint2"])


def wf_add_stories(ctx, env):
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint"]).action_add_stories(
        ctx.ids["sprint"], [ctx.ids["story"]])


def wf_carry_over(ctx, env):
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint"]).action_carry_over(
        [ctx.ids["story"]], ctx.ids["target"], reason="P0-A carry-over race")


def wf_carry_over_b(ctx, env):
    """Opposing direction: story2 lives in sprint2, moves to sprint1."""
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint2"]).action_carry_over(
        [ctx.ids["story2"]], ctx.ids["sprint"], reason="P0-A opposing carry-over")


def wf_carry_over_x(ctx, env):
    """C-02b R1: story (X) lives in sprint 1, moves to sprint 2."""
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint"]).action_carry_over(
        [ctx.ids["story"]], ctx.ids["sprint2"], reason="P0-A opposing carry-over")


def wf_close(ctx, env):
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint"]).action_close()


def wf_points(ctx, env, value=8):
    return env["amnus.agile.user.story"].browse(ctx.ids["story"]).write(
        {"story_points": value})


def wf_points5(ctx, env):
    return wf_points(ctx, env, value=5)


def wf_move_task(ctx, env):
    return env["project.task"].browse(ctx.ids["task"]).write(
        {"project_id": ctx.ids["project2"]})


def wf_link_task(ctx, env):
    return env["amnus.agile.user.story"].browse(ctx.ids["story"]).write(
        {"task_id": ctx.ids["task"]})


def wf_burndown(ctx, env):
    return env["amnus.agile.sprint"].browse(ctx.ids["sprint"])._record_burndown_event(
        "update")


# ---------------------------------------------------------------------------
# Shared invariant queries (read-only, harness ids only)
# ---------------------------------------------------------------------------


def inv_multi_open(conn, story_ids):
    return H.check_empty(conn, "membership: at most one open membership per story", """
        SELECT story_id, count(*) FROM amnus_agile_sprint_membership
         WHERE outcome = 'active' AND date_removed IS NULL AND story_id = ANY(%s)
         GROUP BY story_id HAVING count(*) > 1
    """, (list(story_ids),))


def inv_dup_membership(conn, story_ids):
    return H.check_empty(conn, "membership: no duplicate (sprint, story) rows", """
        SELECT sprint_id, story_id, count(*) FROM amnus_agile_sprint_membership
         WHERE story_id = ANY(%s)
         GROUP BY sprint_id, story_id HAVING count(*) > 1
    """, (list(story_ids),))


def inv_story_membership_consistency(conn, story_ids):
    ids = list(story_ids)
    rows = H.q_rows(conn, """
        -- A: open membership sprint differs from story.sprint_id
        SELECT s.id, 'open_membership_mismatch' FROM amnus_agile_user_story s
        JOIN amnus_agile_sprint_membership m
          ON m.story_id = s.id AND m.outcome = 'active' AND m.date_removed IS NULL
        WHERE s.id = ANY(%s) AND m.sprint_id IS DISTINCT FROM s.sprint_id
        UNION ALL
        -- B: assigned to an open sprint but has no open membership
        SELECT s.id, 'missing_open_membership' FROM amnus_agile_user_story s
        JOIN amnus_agile_sprint p ON p.id = s.sprint_id
        LEFT JOIN amnus_agile_sprint_membership m
          ON m.story_id = s.id AND m.outcome = 'active' AND m.date_removed IS NULL
        WHERE s.id = ANY(%s) AND m.id IS NULL AND p.state NOT IN ('closed', 'cancelled')
        UNION ALL
        -- C: open membership inside a closed/cancelled sprint
        SELECT m.story_id, 'open_membership_in_closed_sprint'
          FROM amnus_agile_sprint_membership m
          JOIN amnus_agile_sprint p ON p.id = m.sprint_id
         WHERE m.story_id = ANY(%s) AND m.outcome = 'active'
           AND m.date_removed IS NULL AND p.state IN ('closed', 'cancelled')
    """, (ids, ids, ids))
    return {"name": "story: sprint assignment matches membership history",
            "ok": not rows, "rows": [list(r) for r in rows[:20]],
            "detail": "consistent" if not rows else f"{len(rows)} violation(s)"}


def inv_burndown_dup(conn, sprint_ids):
    return H.check_empty(conn, "burndown: unique (sprint, date, event_sequence)", """
        SELECT sprint_id, date, event_sequence, count(*)
          FROM amnus_agile_burndown
         WHERE sprint_id = ANY(%s)
         GROUP BY sprint_id, date, event_sequence HAVING count(*) > 1
    """, (list(sprint_ids),))


def inv_burndown_gap(conn, sprint_ids):
    return H.check_empty(conn, "burndown: no gaps (count == max sequence)", """
        SELECT sprint_id, count(*), max(event_sequence)
          FROM amnus_agile_burndown
         WHERE sprint_id = ANY(%s)
         GROUP BY sprint_id
        HAVING count(*) <> max(event_sequence)
    """, (list(sprint_ids),))


def inv_closed_frozen(conn, sprint_ids):
    return H.check_empty(conn, "sprint: closed metrics frozen and coherent", """
        SELECT id, state, committed_points, final_committed_points,
               completed_points, final_completed_points, velocity_points
          FROM amnus_agile_sprint
         WHERE id = ANY(%s) AND state = 'closed'
           AND (committed_points IS DISTINCT FROM final_committed_points
             OR completed_points IS DISTINCT FROM final_completed_points
             OR velocity_points IS DISTINCT FROM final_completed_points
             OR final_carry_over_points IS DISTINCT FROM
                (final_committed_points - final_completed_points))
    """, (list(sprint_ids),))


def inv_task_story_project(conn, story_ids):
    return H.check_empty(conn, "task/story: no cross-project or cross-company link", """
        SELECT s.id, s.project_id, t.id, t.project_id, s.company_id, t.company_id
          FROM amnus_agile_user_story s
          JOIN project_task t ON t.id = s.task_id
         WHERE s.id = ANY(%s)
           AND (t.project_id IS DISTINCT FROM s.project_id
             OR t.company_id IS DISTINCT FROM s.company_id)
    """, (list(story_ids),))


def inv_sprint_state(conn, sprint_id, expected_state):
    row = H.q_rows(conn, "SELECT state FROM amnus_agile_sprint WHERE id = %s",
                   (sprint_id,))
    got = row[0][0] if row else None
    return {"name": f"sprint state == {expected_state}", "ok": got == expected_state,
            "value": got, "detail": f"state={got}"}


def inv_scalar_eq(conn, name, sql, params, expected):
    row = H.q_rows(conn, sql, params)
    got = row[0][0] if row else None
    return {"name": name, "ok": got == expected, "value": got,
            "detail": f"got={got}, expected={expected}"}


# ---------------------------------------------------------------------------
# Outcome expectations (REQUIRED behaviour)
# ---------------------------------------------------------------------------


def _sqlstate_evidence(o) -> str:
    """Human-readable places where a given SQLSTATE was observed."""
    parts = []
    if (o.workflow_error or {}).get("sqlstate"):
        parts.append(f"workflow_error={o.workflow_error['sqlstate']}")
    if (o.runner_error or {}).get("sqlstate"):
        parts.append(f"runner_error={o.runner_error['sqlstate']}")
    for e in o.retry_events:
        if e.get("sqlstate"):
            parts.append(f"retried_try{e.get('try')}:{e['sqlstate']}"
                         f"({e.get('label')})")
    return ", ".join(parts) if parts else "none"


def _outcome_checks(ctx, spec: dict) -> list[dict]:
    checks = []
    for role, rules in spec.items():
        o = ctx.outcomes[role]
        prefix = f"{role}"
        checks.append({"name": f"{prefix}: no runner/protocol error",
                       "ok": o.runner_error is None,
                       "detail": (o.runner_error or {}).get("type")
                       if o.runner_error else "none"})
        if "status" in rules:
            checks.append({"name": f"{prefix}: status == {rules['status']}",
                           "ok": o.status == rules["status"],
                           "detail": o.status})
        if "statuses" in rules:
            checks.append({"name": f"{prefix}: status in {rules['statuses']}",
                           "ok": o.status in rules["statuses"], "detail": o.status})
        if rules.get("no_workflow_error"):
            checks.append({"name": f"{prefix}: workflow succeeded",
                           "ok": o.workflow_error is None,
                           "detail": (o.workflow_error or {}).get("type")
                           if o.workflow_error else "none"})
        if "error_type" in rules:
            got = (o.workflow_error or {}).get("type")
            checks.append({"name": f"{prefix}: controlled {rules['error_type']}",
                           "ok": got == rules["error_type"], "detail": str(got)})
        if rules.get("no_deadlock"):
            seen = o.any_sqlstate("40P01")
            checks.append({"name": f"{prefix}: no deadlock SQLSTATE",
                           "ok": not seen,
                           "detail": _sqlstate_evidence(o) if seen else "none"})
        if rules.get("deadlock"):
            seen = o.any_sqlstate("40P01")
            checks.append({"name": f"{prefix}: deadlock SQLSTATE 40P01",
                           "ok": seen,
                           "detail": _sqlstate_evidence(o)})
    return checks


def _overlap_check(ctx) -> dict:
    pids = [o.pid for o in ctx.outcomes.values() if o.pid]
    if len(pids) < 2:
        return {"name": "overlap: two distinct backend pids", "ok": False,
                "detail": f"pids={pids}"}
    since = ctx.since()
    blocking = ctx.observer.evidence_window(pids, since=since)
    if blocking:
        sample = blocking[0]
        return {"name": "overlap: PostgreSQL lock-wait between workers",
                "ok": True, "detail": {
                    "mode": "lock_wait",
                    "t": sample["t"],
                    "blocked": sample["blocked"],
                    "xids": sample["xids"],
                    "samples": len(blocking),
                }}
    # Window evidence: both transactions alive in the same pg sample with
    # distinct xids, and workflow execution windows nested (timestamps).
    sample = None
    with ctx.observer._cond:
        for s in ctx.observer._samples:
            if since is not None and s["tm"] < since:
                continue
            act = [s["activity"].get(p) for p in pids]
            xids = {x["xid"] for x in s["xids"] if x["pid"] in pids}
            if all(act) and len(xids) >= 2:
                sample = {"t": s["t"],
                          "activity": {p: s["activity"][p] for p in pids},
                          "xids": [x for x in s["xids"] if x["pid"] in pids]}
                break
    starts = [o.t_start for o in ctx.outcomes.values() if o.t_start]
    ends = [o.t_tend for o in ctx.outcomes.values() if o.t_tend]
    nested = bool(starts and ends and max(starts) < min(ends))
    ok = sample is not None and nested
    return {"name": "overlap: concurrent transactions evidenced by PostgreSQL",
            "ok": ok,
            "detail": {"mode": "concurrent_transactions" if ok else "insufficient",
                       "sample": sample,
                       "window": {"max_start": max(starts) if starts else None,
                                  "min_end": min(ends) if ends else None}}}


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------


class Scenario:
    def __init__(self, key, description, setup, roles, expect, invariants,
                 overlap_required=True):
        self.key = key
        self.description = description
        self.setup = setup
        self.roles = roles           # {"R1": fn, "R2": fn}
        self.expect = expect         # dict role -> rules (or callable(ctx))
        self.invariants = invariants  # callable(conn, ids) -> [dict]
        self.overlap_required = overlap_required


def _common_invariants(conn, ids):
    checks = []
    checks.append(inv_multi_open(conn, ids["all_stories"]))
    checks.append(inv_dup_membership(conn, ids["all_stories"]))
    checks.append(inv_story_membership_consistency(conn, ids["all_stories"]))
    checks.append(inv_burndown_dup(conn, ids["all_sprints"]))
    checks.append(inv_burndown_gap(conn, ids["all_sprints"]))
    checks.append(inv_closed_frozen(conn, ids["all_sprints"]))
    return checks


# -- C-01 ------------------------------------------------------------------

def _setup_c01(fx, rep):
    project = fx.project("main")
    sprint = fx.sprint(f"C-01 sprint #{rep}", project, "2026-02-02", "2026-02-15")
    sprint.action_plan()
    story = fx.story(f"C-01 story #{rep}", project, points=3)
    ids = {"sprint": sprint.id, "story": story.id}
    ids["all_stories"] = [story.id]
    ids["all_sprints"] = [sprint.id]
    return ids


SCENARIOS: dict[str, Scenario] = {}

# Execution phase (set through available()/set_phase by run_concurrency).
# Protocols whose deterministic pre-lock must match the implementation's
# CURRENT lock order branch on this: the pre-fix implementation locks
# sprints before stories in action_add_stories/action_carry_over, the fixed
# implementation locks stories first (global task -> story -> sprint order).
PHASE = "pre_fix"


def set_phase(phase: str) -> None:
    global PHASE
    PHASE = phase


def register(scenario: Scenario) -> None:
    SCENARIOS[scenario.key] = scenario


register(Scenario(
    "C-01",
    "Concurrent duplicate Story membership (same sprint)",
    _setup_c01,
    {
        "R1": holder_block_then_work(
            lambda ids: [("story", [ids["story"]])], wf_add_to_sprint),
        "R2": contender_wait_then_work(wf_add_to_sprint),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "committed", "no_workflow_error": True}},
    lambda conn, ids: _common_invariants(conn, ids) + [
        inv_scalar_eq(conn, "membership: exactly one open membership exists",
                      "SELECT count(*) FROM amnus_agile_sprint_membership "
                      "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
                      (ids["story"],), 1),
        inv_scalar_eq(conn, "membership: open membership belongs to the sprint",
                      "SELECT sprint_id FROM amnus_agile_sprint_membership "
                      "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
                      (ids["story"],), ids["sprint"]),
    ],
))

# -- C-01b -----------------------------------------------------------------


def _setup_c01b(fx, rep):
    project = fx.project("main")
    s1 = fx.sprint(f"C-01b sprint A #{rep}", project, "2026-03-02", "2026-03-15")
    s2 = fx.sprint(f"C-01b sprint B #{rep}", project, "2026-03-16", "2026-03-29")
    s1.action_plan()
    s2.action_plan()
    story = fx.story(f"C-01b story #{rep}", project, points=3)
    ids = {"sprint": s1.id, "sprint2": s2.id, "story": story.id,
           "all_stories": [story.id], "all_sprints": [s1.id, s2.id]}
    return ids


def _inv_c01b(conn, ids):
    checks = _common_invariants(conn, ids)
    checks.append(inv_scalar_eq(
        conn, "membership: single open membership ends in sprint B",
        "SELECT sprint_id FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
        (ids["story"],), ids["sprint2"]))
    checks.append(inv_scalar_eq(
        conn, "membership: sprint A history closed as removed",
        "SELECT outcome FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND sprint_id = %s",
        (ids["story"], ids["sprint"]), "removed"))
    partial = H.q_rows(conn, """
        SELECT m.id, m.sprint_id, m.outcome, m.date_removed, m.create_date,
               m.write_date, m.committed_points, m.final_points, m.added_by_id
          FROM amnus_agile_sprint_membership m
         WHERE m.story_id = %s AND m.outcome <> 'active' AND m.date_removed IS NULL
    """, (ids["story"],))
    checks.append({"name": "membership: no partial (open+closed) state",
                   "ok": not partial,
                   "detail": partial if partial else "none"})
    return checks


register(Scenario(
    "C-01b",
    "Concurrent duplicate Story membership (different active sprints)",
    _setup_c01b,
    {
        "R1": holder_block_then_work(
            lambda ids: [("story", [ids["story"]])], wf_add_to_sprint),
        "R2": contender_wait_then_work(wf_add_to_sprint2),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "committed", "no_workflow_error": True}},
    _inv_c01b,
))

# -- C-02 ------------------------------------------------------------------


def _setup_c02(fx, rep):
    project = fx.project("main")
    src = fx.sprint(f"C-02 source #{rep}", project, "2026-04-02", "2026-04-15")
    tgt = fx.sprint(f"C-02 target #{rep}", project, "2026-04-16", "2026-04-29")
    src.action_plan()
    tgt.action_plan()
    story = fx.story(f"C-02 story #{rep}", project, points=5)
    story.action_add_to_sprint(src.id)
    src.action_start()
    tgt.action_start()
    ids = {"sprint": src.id, "target": tgt.id, "story": story.id,
           "all_stories": [story.id], "all_sprints": [src.id, tgt.id]}
    return ids


def _inv_c02(conn, ids):
    checks = _common_invariants(conn, ids)
    checks.append(inv_scalar_eq(
        conn, "membership: open membership only in target sprint",
        "SELECT sprint_id FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
        (ids["story"],), ids["target"]))
    checks.append(inv_scalar_eq(
        conn, "membership: source closed as carried_over -> target",
        "SELECT carry_over_sprint_id FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND sprint_id = %s AND outcome = 'carried_over'",
        (ids["story"], ids["sprint"]), ids["target"]))
    checks.append(inv_scalar_eq(
        conn, "history: source carry_over_out event recorded",
        "SELECT count(*) FROM amnus_agile_burndown "
        "WHERE sprint_id = %s AND event_type = 'carry_over_out'",
        (ids["sprint"],), 1))
    checks.append(inv_scalar_eq(
        conn, "history: target carry_over_in event recorded once",
        "SELECT count(*) FROM amnus_agile_burndown "
        "WHERE sprint_id = %s AND event_type = 'carry_over_in'",
        (ids["target"],), 1))
    checks.append(inv_scalar_eq(
        conn, "story: sprint assignment follows carry-over",
        "SELECT sprint_id FROM amnus_agile_user_story WHERE id = %s",
        (ids["story"],), ids["target"]))
    return checks


register(Scenario(
    "C-02",
    "Concurrent carry-over of the same Story to the same target sprint",
    _setup_c02,
    {
        "R1": holder_block_then_work(
            # Pre-lock must match the implementation's lock order or the two
            # workers would deadlock in the harness itself: pre_fix acquires
            # sprints first; post_fix acquires the story first, then sprints.
            lambda ids: (
                [("story", [ids["story"]]),
                 ("sprint", sorted([ids["sprint"], ids["target"]]))]
                if PHASE == "post_fix" else
                [("sprint", sorted([ids["sprint"], ids["target"]]))]
            ),
            wf_carry_over),
        "R2": contender_wait_then_work(wf_carry_over),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "rolled_back", "error_type": "UserError"}},
    _inv_c02,
))

# -- C-02b (opposing source/target, deadlock-order test) --------------------


def _setup_c02b(fx, rep):
    project = fx.project("main")
    s1 = fx.sprint(f"C-02b sprint 1 #{rep}", project, "2026-05-02", "2026-05-15")
    s2 = fx.sprint(f"C-02b sprint 2 #{rep}", project, "2026-05-16", "2026-05-29")
    s1.action_plan()
    s2.action_plan()
    x = fx.story(f"C-02b story X #{rep}", project, points=3)
    y = fx.story(f"C-02b story Y #{rep}", project, points=5)
    x.action_add_to_sprint(s1.id)
    y.action_add_to_sprint(s2.id)
    s1.action_start()
    s2.action_start()
    ids = {"sprint": s1.id, "sprint2": s2.id, "story": x.id, "story2": y.id,
           "all_stories": [x.id, y.id], "all_sprints": [s1.id, s2.id]}
    return ids


def _inv_c02b(conn, ids):
    checks = _common_invariants(conn, ids)
    checks.append(inv_scalar_eq(
        conn, "membership: story X open in sprint 2",
        "SELECT sprint_id FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
        (ids["story"],), ids["sprint2"]))
    checks.append(inv_scalar_eq(
        conn, "membership: story Y open in sprint 1",
        "SELECT sprint_id FROM amnus_agile_sprint_membership "
        "WHERE story_id = %s AND outcome = 'active' AND date_removed IS NULL",
        (ids["story2"],), ids["sprint"]))
    return checks


register(Scenario(
    "C-02b",
    "Opposing source/target carry-overs (S1->S2 vs S2->S1) - lock-order test",
    _setup_c02b,
    {
        "R1": holder_block_then_work(
            # Phase-aware pre-lock (see C-02): post_fix locks story first.
            lambda ids: (
                [("story", [ids["story"]]),
                 ("sprint", sorted([ids["sprint"], ids["sprint2"]]))]
                if PHASE == "post_fix" else
                [("sprint", sorted([ids["sprint"], ids["sprint2"]]))]
            ),
            wf_carry_over_x),
        "R2": contender_wait_then_work(wf_carry_over_b),
    },
    {"R1": {"status": "committed", "no_workflow_error": True, "no_deadlock": True},
     "R2": {"statuses": ("committed", "rolled_back"), "no_deadlock": True}},
    _inv_c02b,
))

# -- C-03 ------------------------------------------------------------------


def _setup_c03(fx, rep):
    project = fx.project("main")
    sprint = fx.sprint(f"C-03 sprint #{rep}", project, "2026-06-01", "2026-06-14")
    sprint.action_plan()
    done_story = fx.story(f"C-03 story done #{rep}", project, points=3)
    open_story = fx.story(f"C-03 story open #{rep}", project, points=5)
    done_story.action_add_to_sprint(sprint.id)
    open_story.action_add_to_sprint(sprint.id)
    sprint.action_start()
    done_story.action_start()
    done_story.write({"acceptance_criteria": "P0-A closure race"})
    done_story.action_done()
    ids = {"sprint": sprint.id, "story": done_story.id, "story2": open_story.id,
           "all_stories": [done_story.id, open_story.id], "all_sprints": [sprint.id]}
    return ids


def _inv_c03(conn, ids):
    checks = _common_invariants(conn, ids)
    checks.append(inv_sprint_state(conn, ids["sprint"], "closed"))
    checks.append(inv_scalar_eq(
        conn, "sprint: final committed = 8", "SELECT final_committed_points "
        "FROM amnus_agile_sprint WHERE id = %s", (ids["sprint"],), 8))
    checks.append(inv_scalar_eq(
        conn, "sprint: final completed = 3", "SELECT final_completed_points "
        "FROM amnus_agile_sprint WHERE id = %s", (ids["sprint"],), 3))
    checks.append(inv_scalar_eq(
        conn, "sprint: velocity = 3", "SELECT velocity_points "
        "FROM amnus_agile_sprint WHERE id = %s", (ids["sprint"],), 3))
    checks.append(inv_scalar_eq(
        conn, "history: exactly one closure event",
        "SELECT count(*) FROM amnus_agile_burndown "
        "WHERE sprint_id = %s AND event_type = 'closure'", (ids["sprint"],), 1))
    checks.append(inv_scalar_eq(
        conn, "membership: completed story closed as completed",
        "SELECT outcome FROM amnus_agile_sprint_membership WHERE story_id = %s",
        (ids["story"],), "completed"))
    checks.append(inv_scalar_eq(
        conn, "membership: open story closed as incomplete",
        "SELECT outcome FROM amnus_agile_sprint_membership WHERE story_id = %s",
        (ids["story2"],), "incomplete"))
    checks.append(inv_scalar_eq(
        conn, "membership: no open memberships left in closed sprint",
        "SELECT count(*) FROM amnus_agile_sprint_membership "
        "WHERE sprint_id = %s AND outcome = 'active' AND date_removed IS NULL",
        (ids["sprint"],), 0))
    return checks


register(Scenario(
    "C-03",
    "Concurrent Sprint closure by two managers",
    _setup_c03,
    {
        "R1": holder_block_then_work(
            lambda ids: [("sprint", [ids["sprint"]])], wf_close),
        "R2": contender_wait_then_work(wf_close),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "rolled_back", "error_type": "UserError"}},
    _inv_c03,
))

# -- C-04a (closure locks first, then points update arrives) ----------------


def _setup_c04(fx, rep, tag):
    project = fx.project("main")
    sprint = fx.sprint(f"{tag} sprint #{rep}", project, "2026-07-01", "2026-07-14")
    sprint.action_plan()
    story = fx.story(f"{tag} story #{rep}", project, points=3)
    story.action_add_to_sprint(sprint.id)
    sprint.action_start()
    ids = {"sprint": sprint.id, "story": story.id,
           "all_stories": [story.id], "all_sprints": [sprint.id]}
    return ids


def _setup_c04a(fx, rep):
    return _setup_c04(fx, rep, "C-04a")


def _inv_c04_final_matches_stories(conn, ids):
    """Final frozen metrics must equal the accepted serialized story state."""
    checks = _common_invariants(conn, ids)
    checks.append(inv_scalar_eq(
        conn, "sprint: final committed equals story points sum",
        "SELECT s.final_committed_points FROM amnus_agile_sprint s WHERE s.id = %s",
        (ids["sprint"],),
        H.q_rows(conn, "SELECT COALESCE(sum(story_points), 0) FROM amnus_agile_user_story "
                       "WHERE sprint_id = %s AND state <> 'cancelled'",
                 (ids["sprint"],))[0][0]))
    checks.append(inv_scalar_eq(
        conn, "sprint: state closed after closure race",
        "SELECT state FROM amnus_agile_sprint WHERE id = %s",
        (ids["sprint"],), "closed"))
    return checks


register(Scenario(
    "C-04a",
    "Story points update vs Sprint closure - closure acquires the sprint lock first",
    _setup_c04a,
    {
        "R1": holder_block_then_work(
            lambda ids: [("sprint", [ids["sprint"]])], wf_close),
        "R2": contender_wait_then_work(lambda ctx, env: wf_points(ctx, env, 8)),
    },
    # Required behaviour: the points update must never silently land on a
    # finalized sprint (it must be a controlled rejection -> rollback).
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "rolled_back"}},
    _inv_c04_final_matches_stories,
))

# -- C-04b (points update locks first, then closure) ------------------------


def _setup_c04b(fx, rep):
    return _setup_c04(fx, rep, "C-04b")


register(Scenario(
    "C-04b",
    "Story points update vs Sprint closure - points update acquires locks first",
    _setup_c04b,
    {
        "R1": holder_block_then_work(
            lambda ids: [("story", [ids["story"]]), ("sprint", [ids["sprint"]])],
            lambda ctx, env: wf_points(ctx, env, 8)),
        "R2": contender_wait_then_work(wf_close),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "committed", "no_workflow_error": True}},
    _inv_c04_final_matches_stories,
))

# -- C-05a (task move pending vs story link) --------------------------------


def _setup_c05(fx, rep, tag):
    p1 = fx.project("main")
    p2 = fx.project("second")
    story = fx.story(f"{tag} story #{rep}", p1, points=3)
    task = fx.task(f"{tag} task #{rep}", p1)
    ids = {"story": story.id, "task": task.id, "project2": p2.id,
           "all_stories": [story.id], "all_sprints": []}
    return ids


def _setup_c05a(fx, rep):
    return _setup_c05(fx, rep, "C-05a")


def c05a_holder(ctx, env, cr, o):
    """Mover: prelock task -> perform the move (uncommitted) -> release contender
    -> wait until the link attempt finished or blocked -> let runner commit."""
    pairs = [("task", [ctx.ids["task"]])]
    ctx.notes["R1_PRELOCK"] = H.prelock(cr, pairs)
    H.call(o, "task.write(project_id)", lambda: wf_move_task(ctx, env),
           cr=cr, env=env, prelock_pairs=pairs)
    ctx.sync.set("R1_LOCKED")

    def pred():
        if ctx.sync.is_set("R2_DONE"):
            return "contender_finished"
        r2pid = ctx.outcomes["R2"].pid
        if r2pid:
            s = ctx.observer.latest_for([r2pid], since=ctx.since())
            if s:
                act = s["activity"].get(r2pid) or {}
                if o.pid in act.get("blockers", []):
                    return "contender_blocked"
        return None

    ctx.notes["C05A_WAIT"] = H.wait_until(pred, SYNC, "link attempt done or blocked")


def c05a_contender(ctx, env, cr, o):
    if not ctx.sync.wait("R1_LOCKED", SYNC):
        raise TimeoutError("mover never locked/moved")
    H.call(o, "story.write(task_id)", lambda: wf_link_task(ctx, env),
           cr=cr, env=env)
    ctx.sync.set("R2_DONE")


register(Scenario(
    "C-05a",
    "Task project reassignment (uncommitted) vs Story task linking",
    _setup_c05a,
    {"R1": c05a_holder, "R2": c05a_contender},
    # Required: no cross-project link may exist; the losing attempt must not
    # silently produce a contradictory combination.
    {"R1": {"statuses": ("committed", "rolled_back")},
     "R2": {"statuses": ("committed", "rolled_back")}},
    lambda conn, ids: _common_invariants(conn, ids) + [inv_task_story_project(conn, ids["all_stories"])],
))

# -- C-05b (link committed first, then move is attempted) -------------------


def _setup_c05b(fx, rep):
    return _setup_c05(fx, rep, "C-05b")


register(Scenario(
    "C-05b",
    "Story task linking committed first vs later Task project reassignment",
    _setup_c05b,
    {
        "R1": holder_block_then_work(
            lambda ids: [("task", [ids["task"]])], wf_link_task),
        "R2": contender_wait_then_work(wf_move_task),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "rolled_back", "error_type": "UserError"}},
    lambda conn, ids: _common_invariants(conn, ids) + [
        inv_task_story_project(conn, ids["all_stories"]),
        inv_scalar_eq(conn, "task stays in the story's project",
                      "SELECT project_id FROM project_task WHERE id = %s",
                      (ids["task"],),
                      H.q_rows(conn, "SELECT project_id FROM amnus_agile_user_story "
                                     "WHERE id = %s", (ids["story"],))[0][0]),
    ],
))

# -- C-06 ------------------------------------------------------------------


def _setup_c06(fx, rep):
    project = fx.project("main")
    sprint = fx.sprint(f"C-06 sprint #{rep}", project, "2026-08-03", "2026-08-16")
    sprint.action_plan()
    sprint.action_start()          # baseline event, sequence 1
    ids = {"sprint": sprint.id, "all_stories": [], "all_sprints": [sprint.id]}
    return ids


def _inv_c06(conn, ids):
    checks = _common_invariants(conn, ids)
    checks.append(inv_scalar_eq(
        conn, "burndown: baseline + 2 committed events",
        "SELECT count(*) FROM amnus_agile_burndown WHERE sprint_id = %s",
        (ids["sprint"],), 3))
    checks.append(inv_scalar_eq(
        conn, "burndown: sequences contiguous (count == max)",
        "SELECT count(*) FROM amnus_agile_burndown WHERE sprint_id = %s",
        (ids["sprint"],),
        H.q_rows(conn, "SELECT max(event_sequence) FROM amnus_agile_burndown "
                       "WHERE sprint_id = %s", (ids["sprint"],))[0][0]))
    checks.append(H.check_empty(conn, "burndown: no duplicate sequences at all", """
        SELECT event_sequence FROM amnus_agile_burndown
         WHERE sprint_id = %s GROUP BY event_sequence HAVING count(*) > 1
    """, (ids["sprint"],)))
    checks.append(inv_scalar_eq(
        conn, "sprint: still active (events did not mutate state)",
        "SELECT state FROM amnus_agile_sprint WHERE id = %s",
        (ids["sprint"],), "active"))
    return checks


register(Scenario(
    "C-06",
    "Concurrent Burndown event allocation on the same sprint",
    _setup_c06,
    {
        "R1": holder_block_then_work(
            lambda ids: [("sprint", [ids["sprint"]])], wf_burndown),
        "R2": contender_wait_then_work(wf_burndown),
    },
    {"R1": {"status": "committed", "no_workflow_error": True},
     "R2": {"status": "committed", "no_workflow_error": True}},
    _inv_c06,
))

# -- S-01 (opposing lock-order / deadlock stress) ---------------------------
# The holder pre-locks the FIRST lock of its real workflow, which depends on
# the implementation's current lock order: before the fix, action_add_stories
# locks the sprint first; after the fix it locks the story first.


def _setup_s01(fx, rep):
    project = fx.project("main")
    s0 = fx.sprint(f"S-01 origin sprint #{rep}", project, "2026-09-07", "2026-09-20")
    s1 = fx.sprint(f"S-01 target sprint #{rep}", project, "2026-09-21", "2026-10-04")
    s0.action_plan()
    s1.action_plan()
    story = fx.story(f"S-01 story #{rep}", project, points=3)
    story.action_add_to_sprint(s0.id)
    ids = {"sprint": s1.id, "sprint0": s0.id, "story": story.id,
           "all_stories": [story.id], "all_sprints": [s0.id, s1.id]}
    return ids


def _inv_s01(conn, ids):
    checks = _common_invariants(conn, ids)
    # Whichever transaction survived, membership history must be coherent:
    # story is either still in the origin sprint or moved to the target.
    rows = H.q_rows(conn, """
        SELECT s.sprint_id,
               (SELECT count(*) FROM amnus_agile_sprint_membership m
                 WHERE m.story_id = s.id AND m.outcome = 'active'
                   AND m.date_removed IS NULL)
          FROM amnus_agile_user_story s WHERE s.id = %s
    """, (ids["story"],))
    sprint_of_story, open_count = rows[0] if rows else (None, None)
    coherent = open_count == 1 and sprint_of_story in (ids["sprint"], ids["sprint0"])
    checks.append({"name": "story: exactly one open membership in a valid sprint "
                           "regardless of deadlock victim",
                   "ok": coherent,
                   "detail": f"sprint={sprint_of_story}, open={open_count}, "
                             f"origin={ids['sprint0']}, target={ids['sprint']}"})
    return checks


def s01_holder(phase):
    def role(ctx, env, cr, o):
        if phase == "pre_fix":
            pairs = [("sprint", [ctx.ids["sprint"]])]
        else:
            pairs = [("story", [ctx.ids["story"]])]
        ctx.notes["R1_PRELOCK"] = H.prelock(cr, pairs)
        ctx.sync.set("R1_LOCKED")
        sample = ctx.observer.wait_blocked(ctx.role_pid("R2"), o.pid, SYNC,
                                           since=ctx.since())
        ctx.notes["OVERLAP"] = sample
        H.call(o, "sprint.action_add_stories", lambda: wf_add_stories(ctx, env),
               cr=cr, env=env, prelock_pairs=pairs)
    return role


def s01_expected_checks(ctx, phase):
    spec = {"R1": {"no_deadlock": True, "statuses": ("committed", "rolled_back")},
            "R2": {"no_deadlock": True, "statuses": ("committed", "rolled_back")}}
    checks = _outcome_checks(ctx, spec)
    if phase == "pre_fix":
        # Demonstration run: we REQUIRE the deadlock to be observed (defect
        # evidence).  The post-fix run uses the no_deadlock spec above.
        # NOTE: with the emulated service layer a 40P01 may be absorbed by a
        # successful retry, so we look at retry_events as well.
        checks = [
            {"name": "deadlock detected on at least one role (defect evidence)",
             "ok": any(ctx.outcomes[r].any_sqlstate("40P01")
                       for r in ("R1", "R2")),
             "detail": {r: _sqlstate_evidence(ctx.outcomes[r])
                        for r in ("R1", "R2")}},
        ]
    return checks


def register_s01(phase: str) -> None:
    def expect(ctx):
        return s01_expected_checks(ctx, phase)

    def invariants(conn, ids):
        return _inv_s01(conn, ids)

    key = f"S-01[{phase}]"
    SCENARIOS[key] = Scenario(
        key,
        "Opposing lock order stress: sprint.action_add_stories (sprint-first) vs "
        "story add-to-sprint (story-first)",
        _setup_s01,
        {"R1": s01_holder(phase), "R2": contender_wait_then_work(wf_add_to_sprint)},
        expect,
        invariants,
    )


def register_s01_natural() -> None:
    """Organic stress: no prelock, both workflows released on a GO barrier."""
    SCENARIOS["S-01n"] = Scenario(
        "S-01n",
        "Organic (no prelock) stress of the opposing lock-order pair",
        _setup_s01,
        {"R1": natural_go_then_work(wf_add_stories),
         "R2": natural_go_then_work(wf_add_to_sprint)},
        lambda ctx: [
            {"name": f"{r}: no runner error",
             "ok": ctx.outcomes[r].runner_error is None,
             "detail": (ctx.outcomes[r].runner_error or {}).get("type")}
            for r in ("R1", "R2")
        ] + [{"name": "no deadlock SQLSTATE on any role",
              "ok": all(not ctx.outcomes[r].any_sqlstate("40P01")
                        for r in ("R1", "R2")),
              "detail": {r: _sqlstate_evidence(ctx.outcomes[r])
                         for r in ("R1", "R2")}}],
        _inv_s01,
        overlap_required=False,   # organic stress may not always contend
    )


# Scenario keys are registered dynamically for S-01 by run_concurrency based on
# the phase; expose factories here.
def available(keys_phase: str = "pre_fix") -> dict:
    set_phase(keys_phase)
    register_s01(keys_phase)
    register_s01_natural()
    return SCENARIOS
