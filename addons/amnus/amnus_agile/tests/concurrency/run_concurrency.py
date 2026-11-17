# -*- coding: utf-8 -*-
"""Standalone runner for the AMNUS Agile multi-transaction concurrency harness.

Exact execution command (run from the AMNUS repository root):

    "C:\\Program Files\\AmanusERP\\python\\python.exe" ^
      "addons\\amnus\\amnus_agile\\tests\\concurrency\\run_concurrency.py" ^
      -c config\\amnus-test.conf -d amnus_test_19 --phase pre_fix ^
      --repetitions 10 --output "%TEMP%\\p0a_run.json"

Safety gates (hard stops): the effective ``db_name`` must be ``amnus_test_19``
and ``db_filter`` must be ``^amnus_test_19$``; the runtime session database is
re-verified after boot.  Never run this concurrently with any other Odoo
process against ``amnus_test_19``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import harness as H  # noqa: E402
import scenarios as S  # noqa: E402

DEFAULT_ORDER = [
    "C-01", "C-01b", "C-02", "C-02b", "C-03",
    "C-04a", "C-04b", "C-05a", "C-05b", "C-06",
]


def parse_args(argv):
    ap = argparse.ArgumentParser(description="AMNUS P0-A concurrency harness")
    ap.add_argument("--repetitions", type=int, default=10)
    ap.add_argument("--scenarios", type=str, default=None,
                    help="comma separated scenario keys (default: all)")
    ap.add_argument("--output", type=str, default=None)
    ap.add_argument("--phase", choices=["pre_fix", "post_fix"], default="pre_fix")
    ap.add_argument("--ns", type=str, default=None)
    known, rest = ap.parse_known_args(argv)
    return known, rest


# ---------------------------------------------------------------------------
# Cleanup (harness-created ids only; every statement parameterized)
# ---------------------------------------------------------------------------


def _uniq(values):
    return list(dict.fromkeys(int(v) for v in values))


def cleanup(conn, created: dict) -> dict:
    sprints = _uniq(created.get("sprints", []))
    stories = _uniq(created.get("stories", []))
    tasks = _uniq(created.get("tasks", []))
    projects = _uniq(created.get("projects", []))
    users = _uniq(created.get("users", []))
    partners = _uniq(created.get("partners", []))
    stages = []
    if sprints:
        stages.append(("burndown",
                       "DELETE FROM amnus_agile_burndown WHERE sprint_id = ANY(%s)",
                       (sprints,)))
    if sprints or stories:
        stages.append(("membership",
                       "DELETE FROM amnus_agile_sprint_membership "
                       "WHERE sprint_id = ANY(%s) OR story_id = ANY(%s)",
                       (sprints, stories)))
        stages.append(("audit_log",
                       "DELETE FROM amnus_audit_log WHERE "
                       "(model_name = 'amnus.agile.user.story' AND record_id = ANY(%s)) "
                       "OR (model_name = 'amnus.agile.sprint' AND record_id = ANY(%s))",
                       (stories, sprints)))
    if tasks:
        stages.append(("mail_message(task)",
                       "DELETE FROM mail_message WHERE model = 'project.task' "
                       "AND res_id = ANY(%s)", (tasks,)))
        stages.append(("mail_followers(task)",
                       "DELETE FROM mail_followers WHERE res_model = 'project.task' "
                       "AND res_id = ANY(%s)", (tasks,)))
    if stories:
        stages.append(("story", "DELETE FROM amnus_agile_user_story WHERE id = ANY(%s)",
                       (stories,)))
    if sprints:
        stages.append(("sprint", "DELETE FROM amnus_agile_sprint WHERE id = ANY(%s)",
                       (sprints,)))
    if tasks:
        stages.append(("task", "DELETE FROM project_task WHERE id = ANY(%s)", (tasks,)))
    if projects:
        stages.append(("project", "DELETE FROM project_project WHERE id = ANY(%s)",
                       (projects,)))

    result = {"deleted": {}, "errors": []}
    for name, sql, params in stages:
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            result["deleted"][name] = cur.rowcount
            cur.close()
            conn.commit()
        except Exception as exc:  # noqa: BLE001 - capture cleanup failures
            conn.rollback()
            result["errors"].append({"stage": name, "error": H.describe(exc)})
    # Users are removed through the ORM afterwards (cascade of partner,
    # settings, ...); see run() -- recorded here for completeness.
    result["deferred_orm_users"] = users
    result["partners"] = partners
    return result


def residue(conn, ns: str, created: dict) -> list[dict]:
    like = f"[P0A:{ns}%"
    out = []
    checks = [
        ("amnus_agile_sprint", "name"),
        ("amnus_agile_user_story", "name"),
        ("project_project", "name"),
        ("project_task", "name"),
    ]
    for table, col in checks:
        # NOTE: some columns (e.g. project_project.name, project_task.name) are
        # translated fields stored as jsonb in Odoo 19 -> cast to text first.
        rows = H.q_rows(conn, f"SELECT count(*) FROM {table} WHERE {col}::text LIKE %s",
                        (like,))
        out.append({"table": table, "count": rows[0][0]})
    if created.get("users"):
        rows = H.q_rows(conn, "SELECT count(*) FROM res_users WHERE id = ANY(%s)",
                        (list(created["users"]),))
        out.append({"table": "res_users (harness ids)", "count": rows[0][0]})
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args, odoo_args = parse_args(sys.argv[1:])
    ns = args.ns or time.strftime("%Y%m%dT%H%M%S")
    sc_map = S.available(args.phase)
    if args.scenarios:
        keys = [k.strip() for k in args.scenarios.split(",") if k.strip()]
    else:
        keys = [k for k in DEFAULT_ORDER if k in sc_map] + [
            k for k in (f"S-01[{args.phase}]", "S-01n") if k in sc_map]
    unknown = [k for k in keys if k not in sc_map]
    if unknown:
        raise SystemExit(f"unknown scenario keys: {unknown}")

    started = time.time()
    report = {
        "run_ns": ns,
        "phase": args.phase,
        "repetitions": args.repetitions,
        "scenarios": keys,
        "started_at": H.wall(),
        "results": [],
        "cleanup": None,
        "residue": None,
        "fatal": None,
    }

    print(f"[p0a] boot phase={args.phase} ns={ns} scenarios={keys} "
          f"reps={args.repetitions}", flush=True)
    registry, config = H.boot(odoo_args)
    report["db_config_gate"] = H.verify_db_config()

    import odoo
    from odoo import api

    created = {"users": [], "partners": [], "projects": [], "tasks": [],
               "sprints": [], "stories": []}
    observer = None
    # NOTE: this cursor must stay OPEN for the entire run: scenario fixtures
    # are created through ``env`` (bound to it) between repetitions and
    # committed with ``env.cr.commit()`` after each setup. It is closed in the
    # ``finally`` below. Never wrap it in ``with registry.cursor()``.
    setup_cr = None
    try:
        # ---- setup: manager users, shared context, runtime db check -------
        setup_cr = registry.cursor()
        cr = setup_cr
        db_check = H.check_current_db(cr)
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})
        users_model = env["res.users"]
        group_field = ("group_ids" if "group_ids" in users_model._fields
                       else "groups_id")
        groups = [env.ref("base.group_user").id,
                  env.ref("amnus_agile.group_amnus_agile_manager").id]
        proj_group = env.ref("project.group_project_user", raise_if_not_found=False)
        if proj_group:
            groups.append(proj_group.id)
        company_id = env.company.id
        context = dict(env["res.users"].context_get())
        context["allowed_company_ids"] = [company_id]
        m1 = users_model.create({
            "name": f"[P0A:{ns}] manager 1", "login": f"p0a_{ns}_m1",
            "company_id": company_id, "company_ids": [(6, 0, [company_id])],
            group_field: [(6, 0, groups)],
        })
        m2 = users_model.create({
            "name": f"[P0A:{ns}] manager 2", "login": f"p0a_{ns}_m2",
            "company_id": company_id, "company_ids": [(6, 0, [company_id])],
            group_field: [(6, 0, groups)],
        })
        is_mgr = [env["res.users"].browse(u.id).has_group(
            "amnus_agile.group_amnus_agile_manager") for u in (m1, m2)]
        if not all(is_mgr):
            raise SystemExit(f"SAFETY STOP: manager group not applied: {is_mgr}")
        created["users"] = [m1.id, m2.id]
        created["partners"] = [m1.partner_id.id, m2.partner_id.id]
        cr.commit()
        report["setup"] = {"db_check": db_check, "users": created["users"],
                           "partners": created["partners"],
                           "company_id": company_id, "context": dict(context)}

        observer = H.Observer(H.dsn(config))
        observer.start()

        uids = {"R1": created["users"][0], "R2": created["users"][1]}

        # ---- scenario repetitions ----------------------------------------
        for key in keys:
            sc = sc_map[key]
            stats = {"pass": 0, "fail": 0}
            for rep in range(1, args.repetitions + 1):
                fx = S.Fixture(env, ns, created)
                ids = sc.setup(fx, rep)
                env.cr.commit()          # fixtures committed before workers start

                sync = H.Sync()
                ctx = H.Ctx(sync, observer, f"{key}#{rep}", ids)
                runners = [H.RoleRunner(role, fn, ctx, registry, uids[role], context)
                           for role, fn in sc.roles.items()]
                for r in runners:
                    r.start()
                hung = []
                for r in runners:
                    r.join(timeout=90)
                    if r.is_alive():
                        hung.append(r.role)

                overlap = S._overlap_check(ctx)
                if not sc.overlap_required and not overlap["ok"]:
                    overlap.setdefault("detail", {})["note"] = (
                        "organic stress: no contention observed in this repetition")
                if callable(sc.expect):
                    expect = sc.expect(ctx)
                elif isinstance(sc.expect, dict):
                    expect = S._outcome_checks(ctx, sc.expect)
                else:
                    expect = list(sc.expect)
                inv_conn = H.raw_connect(config)
                try:
                    inv_checks = sc.invariants(inv_conn, ids)
                finally:
                    inv_conn.close()

                ok = (not hung and all(c["ok"] for c in expect)
                      and all(c["ok"] for c in inv_checks)
                      and (overlap["ok"] or not sc.overlap_required))
                stats["pass" if ok else "fail"] += 1
                rec = {
                    "scenario": key,
                    "rep": rep,
                    "description": sc.description,
                    "result": "PASS" if ok else "FAIL",
                    "hung_roles": hung,
                    "overlap": overlap,
                    "expectation": expect,
                    "invariants": inv_checks,
                    "roles": [ctx.outcomes[r.role].as_dict() for r in runners
                              if r.role in ctx.outcomes],
                    "notes": _jsonable(ctx.notes),
                }
                report["results"].append(rec)
                print(f"[p0a] {key} rep {rep}: {rec['result']}"
                      f" overlap={overlap['ok']}"
                      f" err1={_errbrief(ctx.outcomes.get('R1'))}"
                      f" err2={_errbrief(ctx.outcomes.get('R2'))}", flush=True)
            report.setdefault("aggregate", {})[key] = stats

        # ---- final state: stop observer, cleanup, residue -----------------
        observer.stop()
        observer_error = observer.error
        report["observer"] = {"error": observer_error}

        clean_conn = H.raw_connect(config)
        try:
            report["cleanup"] = cleanup(clean_conn, created)
            report["residue_after_sql"] = residue(clean_conn, ns, created)
        finally:
            clean_conn.close()

        # ORM user removal (cascades partners/settings safely).
        with registry.cursor() as cr:
            uenv = api.Environment(cr, odoo.SUPERUSER_ID, {})
            try:
                uenv["res.users"].browse(created["users"]).unlink()
                cr.commit()
                report["cleanup"]["orm_users_deleted"] = created["users"]
            except Exception as exc:  # noqa: BLE001
                cr.rollback()
                report["cleanup"]["errors"].append(
                    {"stage": "orm res.users unlink", "error": H.describe(exc)})

        final_conn = H.raw_connect(config)
        try:
            report["residue"] = residue(final_conn, ns, created)
        finally:
            final_conn.close()

    except BaseException as exc:  # noqa: BLE001 - never lose the failure
        report["fatal"] = {"error": H.describe(exc),
                           "trace": traceback.format_exc()}
        print(f"[p0a] FATAL: {exc}", flush=True)
        if observer is not None:
            observer.stop()
    finally:
        if setup_cr is not None:
            try:
                setup_cr.close()
            except BaseException:  # noqa: BLE001
                pass
        report["finished_at"] = H.wall()
        report["duration_s"] = round(time.time() - started, 1)

    # ---- output ----------------------------------------------------------
    out_path = args.output or os.path.join(
        os.environ.get("TEMP") or os.environ.get("TMP") or ".",
        f"p0a_{args.phase}_{ns}.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)
    print(f"[p0a] report: {out_path}", flush=True)

    agg = report.get("aggregate", {})
    for key, stats in agg.items():
        print(f"[p0a] SUMMARY {key}: pass={stats['pass']} fail={stats['fail']}",
              flush=True)
    total_fail = sum(s["fail"] for s in agg.values())
    if report.get("fatal"):
        print("[p0a] RESULT: FATAL", flush=True)
        return 2
    print(f"[p0a] RESULT: {'ALL PASS' if total_fail == 0 else f'{total_fail} FAILING reps'}",
          flush=True)
    return 0 if total_fail == 0 else 1


def _errbrief(outcome) -> str:
    if outcome is None:
        return "missing"
    retries = ""
    if outcome.retry_events:
        states = [str(e.get("sqlstate") or e.get("type"))
                  for e in outcome.retry_events]
        retries = "+retry[" + ",".join(states) + "]"
    if outcome.workflow_error:
        return f"{outcome.workflow_error['type']}" \
               f"({outcome.workflow_error.get('sqlstate')}){retries}"
    if outcome.runner_error:
        return f"RUNNER:{outcome.runner_error['type']}{retries}"
    return f"ok{retries}" if retries else "ok"


def _jsonable(value):
    try:
        json.dumps(value, default=str)
        return value
    except Exception:  # noqa: BLE001
        return str(value)


if __name__ == "__main__":
    sys.exit(main())
