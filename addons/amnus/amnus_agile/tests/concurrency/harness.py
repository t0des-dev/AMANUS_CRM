# -*- coding: utf-8 -*-
"""Core infrastructure for the AMNUS Agile multi-transaction concurrency harness.

Design guarantees (see docs/sprints/SPRINT_04_5_P0A_CONCURRENCY.md, section 5):

* every role runs in its own thread with its own PostgreSQL connection
  (``registry.cursor()``) and its own Odoo ``Environment`` bound to that cursor;
* no cursor, environment, recordset or transaction is shared between roles;
* overlap is proven from PostgreSQL itself (``pg_stat_activity``,
  ``pg_locks``, ``pg_blocking_pids``) by an independent observer connection,
  never from thread start times or sleeps;
* every wait is bounded (``lock_timeout``/``statement_timeout`` + protocol
  timeouts); there are no *unbounded* retries anywhere;
* commits/rollbacks are owned by the harness and happen only here;
* the ONLY retry loop in the harness is a faithful emulation of Odoo's own
  service layer (``odoo.service.model.retrying``): real RPC requests roll
  back and retry SQLSTATE 40001/40P01/55P03 up to 5 times with a random
  exponential backoff, because Odoo 19 cursors run at REPEATABLE READ
  (``odoo/sql_db.py``). Without this emulation the harness would measure a
  runtime context that does not exist in production. Bounded at
  ``MAX_TRIES = 5`` exactly like Odoo; every retry attempt is recorded.
"""
from __future__ import annotations

import datetime as _dt
import random
import threading
import time
import traceback

# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

LOCK_TIMEOUT = "20000ms"
STATEMENT_TIMEOUT = "60000ms"
SYNC_TIMEOUT = 10.0
# Same bound as odoo.service.model.MAX_TRIES_ON_CONCURRENCY_FAILURE.
MAX_TRIES = 5
# SQLSTATEs retried by odoo.service.model.retrying
# (PG_CONCURRENCY_EXCEPTIONS_TO_RETRY = LockNotAvailable, SerializationFailure,
# DeadlockDetected).
RETRYABLE_SQLSTATES = frozenset({"55P03", "40001", "40P01"})

# Table name -> only ever used with harness-tracked integer ids (parameterized).
LOCK_TABLES = {
    "sprint": "amnus_agile_sprint",
    "story": "amnus_agile_user_story",
    "task": "project_task",
}


def wall() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")


def mono() -> float:
    return time.monotonic()


def describe(exc: BaseException) -> dict:
    """Full, non-swallowed description of an exception (incl. SQLSTATE)."""
    pgcode = getattr(exc, "pgcode", None)
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "sqlstate": pgcode,
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:],
    }


class Outcome:
    """Everything recorded for one worker role of one scenario repetition."""

    def __init__(self, role: str):
        self.role = role
        self.pid: int | None = None
        self.txid: str | None = None
        self.started_at: str | None = None
        self.ended_at: str | None = None
        self.t_start: float | None = None
        self.t_tend: float | None = None
        self.status = "not_started"          # committed | rolled_back | error
        self.actions: list[dict] = []
        self.workflow_error: dict | None = None   # set by call() on FINAL failure
        self.runner_error: dict | None = None
        # Transient concurrency errors absorbed by the emulated service layer
        # (odoo.service.model.retrying). Recorded so defect evidence such as
        # SQLSTATE 40P01 stays visible even when a later try succeeds.
        self.retry_events: list[dict] = []

    def as_dict(self) -> dict:
        return {
            "role": self.role,
            "pid": self.pid,
            "txid": self.txid,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": (round(self.t_tend - self.t_start, 4)
                           if self.t_start and self.t_tend else None),
            "status": self.status,
            "actions": self.actions,
            "workflow_error": self.workflow_error,
            "runner_error": self.runner_error,
            "retry_events": self.retry_events,
        }

    def any_sqlstate(self, sqlstate: str) -> bool:
        """True if this role ever saw ``sqlstate`` (final OR retried try)."""
        for err in [self.workflow_error, self.runner_error, *self.retry_events]:
            if err and err.get("sqlstate") == sqlstate:
                return True
        return False


class Sync:
    """Named events shared by the roles of one repetition."""

    def __init__(self):
        self._lock = threading.Lock()
        self._events: dict[str, threading.Event] = {}

    def _get(self, name: str) -> threading.Event:
        with self._lock:
            if name not in self._events:
                self._events[name] = threading.Event()
            return self._events[name]

    def set(self, name: str) -> None:
        self._get(name).set()

    def is_set(self, name: str) -> bool:
        return self._get(name).is_set()

    def wait(self, name: str, timeout: float = SYNC_TIMEOUT) -> bool:
        return self._get(name).wait(timeout)


def wait_until(predicate, timeout: float, what: str, interval: float = 0.02):
    """Bounded polling for *synchronization* (proof always comes from PostgreSQL)."""
    deadline = mono() + timeout
    while mono() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise TimeoutError(f"timeout after {timeout}s waiting for: {what}")


def prelock(cr, pairs) -> list[dict]:
    """Acquire real row locks the way the workflow itself does (sorted IN list).

    This is a genuine ``SELECT ... FOR UPDATE`` on the exact rows the role's
    real workflow would lock first; it only advances the acquisition timing so
    the overlap becomes deterministic. It is not a mock and never replaces the
    workflow: the full real ORM workflow is executed afterwards by the caller.
    """
    log = []
    for kind, ids in pairs:
        ids = tuple(sorted(int(i) for i in ids))
        if not ids:
            continue
        table = LOCK_TABLES[kind]
        started = wall()
        cr.execute(f"SELECT id FROM {table} WHERE id IN %s FOR UPDATE", (ids,))
        log.append({"kind": kind, "table": table, "ids": list(ids), "at": started,
                    "sql": f"SELECT id FROM {table} WHERE id IN {ids!r} FOR UPDATE"})
    return log


def _is_retryable(exc: BaseException) -> bool:
    """True for the exceptions odoo.service.model.retrying would retry."""
    pgcode = getattr(exc, "pgcode", None)
    if pgcode in RETRYABLE_SQLSTATES:
        return True
    try:
        from odoo.exceptions import ConcurrencyError
    except ImportError:  # pragma: no cover - odoo always present in harness
        return False
    return isinstance(exc, ConcurrencyError)


def _is_integrity_error(exc: BaseException) -> bool:
    """True for psycopg2 IntegrityError (Odoo converts, never retries)."""
    try:
        from psycopg2 import IntegrityError
    except ImportError:  # pragma: no cover
        return False
    return isinstance(exc, IntegrityError)


def call(outcome: Outcome, label: str, fn, cr=None, env=None,
         prelock_pairs=None, max_tries: int = MAX_TRIES):
    """Execute a real workflow method, recording timing/result/exception.

    Odoo 19 runs every cursor at REPEATABLE READ and its service layer
    (``odoo.service.model.retrying``) rolls back and retries SQLSTATE
    40001/40P01/55P03 up to ``MAX_TRIES_ON_CONCURRENCY_FAILURE`` (5) times
    with ``random.uniform(0.0, 2 ** tryno)`` backoff before surfacing the
    error to the client. This function emulates exactly that so observed
    outcomes match production RPC behaviour; there is no other retry in the
    harness and the bound is identical.

    ``prelock_pairs`` re-acquires the harness pre-lock after a rollback (a
    rollback releases it); the pre-lock is a deterministic timing technique
    owned by the harness and never replaces the real workflow, which is
    re-executed in full on every try.
    """
    rec = {"label": label, "t_start": wall(), "t0": mono(), "ok": None,
           "tries": 1}
    value = None
    for tryno in range(1, max_tries + 1):
        rec["tries"] = tryno
        try:
            if tryno > 1 and prelock_pairs and cr is not None:
                prelock(cr, prelock_pairs)
            value = fn()
        except BaseException as exc:  # noqa: BLE001 - every outcome must be captured
            desc = describe(exc)
            if _is_integrity_error(exc):
                # Faithful to odoo.service.model.retrying: an IntegrityError
                # is NOT retried; it is surfaced to the client as a
                # ValidationError ("The operation cannot be completed: ...").
                # The original PG type and SQLSTATE are preserved as evidence.
                desc = dict(desc, pg_type=desc["type"], type="ValidationError",
                            message="The operation cannot be completed: "
                                    + desc["message"])
            if tryno < max_tries and cr is not None and env is not None \
                    and _is_retryable(exc):
                # Emulate odoo.service.model.retrying faithfully:
                outcome.retry_events.append({"try": tryno, "label": label,
                                             **desc})
                cr.rollback()
                env.transaction.reset()
                env.registry.reset_changes()
                time.sleep(random.uniform(0.0, 2 ** tryno))
                continue
            rec["ok"] = False
            rec["error"] = desc
            outcome.workflow_error = desc
            value = None
            break
        else:
            rec["ok"] = True
            if value is not None:
                rec["result"] = repr(value)[:300]
            break
    rec["t_ms"] = round((mono() - rec.pop("t0")) * 1000, 1)
    rec["t_end"] = wall()
    outcome.actions.append(rec)
    return value


class Ctx:
    """Per-repetition shared (but not transactional) context."""

    def __init__(self, sync: Sync, observer: "Observer", ns: str, ids: dict):
        self.sync = sync
        self.observer = observer
        self.ns = ns
        self.ids = ids
        self.outcomes: dict[str, Outcome] = {}
        self.notes: dict = {}

    def outcome(self, role: str) -> Outcome:
        return self.outcomes[role]

    def role_pid(self, role: str) -> int:
        return wait_until(
            lambda: self.outcomes[role].pid, SYNC_TIMEOUT, f"pid of role {role}"
        )

    def since(self) -> float | None:
        """Monotonic start of this repetition, for stale-sample exclusion.

        PostgreSQL reuses backend PIDs across connections, so observer
        evidence must only be accepted from samples taken after the current
        repetition's workers started.
        """
        starts = [o.t_start for o in self.outcomes.values() if o.t_start]
        return min(starts) if starts else None


# ---------------------------------------------------------------------------
# Observer: independent read-only connection proving real overlap
# ---------------------------------------------------------------------------

_ACTIVITY_SQL = """
    SELECT a.pid, a.state, a.wait_event_type, a.wait_event,
           left(a.query, 400) AS query, a.xact_start, a.query_start,
           pg_blocking_pids(a.pid) AS blockers
      FROM pg_stat_activity a
     WHERE a.datname = current_database()
       AND a.backend_type = 'client backend'
"""

_LOCKS_SQL = """
    SELECT pid, locktype, mode, granted,
           CASE WHEN relation IS NOT NULL THEN relation::regclass::text END AS rel
      FROM pg_locks
     WHERE pid = ANY(%s)
"""

_XIDS_SQL = """
    SELECT pid, transactionid
      FROM pg_locks
     WHERE locktype = 'transactionid' AND granted AND pid = ANY(%s)
"""


class Observer(threading.Thread):
    """Samples PostgreSQL lock/wait state on its own connection."""

    def __init__(self, dsn: dict, poll: float = 0.02):
        super().__init__(name="observer", daemon=True)
        self.dsn = dsn
        self.poll = poll
        self._stop_evt = threading.Event()   # NOTE: never name this `_stop`
        self._samples: list[dict] = []
        self._cond = threading.Condition()
        self.error: dict | None = None

    # -- lifecycle ---------------------------------------------------------
    def stop(self) -> None:
        self._stop_evt.set()
        if self.is_alive():
            self.join(timeout=10)

    def run(self) -> None:
        import psycopg2

        try:
            conn = psycopg2.connect(**self.dsn)
            conn.autocommit = True
        except Exception as exc:  # noqa: BLE001
            self.error = describe(exc)
            return
        try:
            consecutive_errors = 0
            while not self._stop_evt.is_set():
                try:
                    sample = self._snapshot(conn)
                except Exception as exc:  # noqa: BLE001
                    # Tolerate transient snapshot failures; only give up after
                    # many consecutive errors (recorded for the report).
                    consecutive_errors += 1
                    self.error = describe(exc)
                    if consecutive_errors >= 50:
                        break
                    time.sleep(self.poll)
                    continue
                consecutive_errors = 0
                self.error = None
                with self._cond:
                    self._samples.append(sample)
                    self._cond.notify_all()
                time.sleep(self.poll)
        finally:
            conn.close()

    def _snapshot(self, conn) -> dict:
        cur = conn.cursor()
        cur.execute(_ACTIVITY_SQL)
        activity = {}
        for row in cur.fetchall():
            activity[row[0]] = {
                "pid": row[0], "state": row[1], "wait_event_type": row[2],
                "wait_event": row[3], "query": row[4],
                "xact_start": row[5].isoformat() if row[5] else None,
                "query_start": row[6].isoformat() if row[6] else None,
                "blockers": list(row[7] or []),
            }
        cur.execute("SELECT pid FROM pg_stat_activity WHERE datname = current_database()")
        pids = [r[0] for r in cur.fetchall()]
        locks, xids = [], []
        if pids:
            cur.execute(_LOCKS_SQL, (pids,))
            locks = [
                {"pid": r[0], "locktype": r[1], "mode": r[2], "granted": r[3],
                 "rel": r[4]}
                for r in cur.fetchall()
            ]
            cur.execute(_XIDS_SQL, (pids,))
            xids = [{"pid": r[0], "xid": str(r[1])} for r in cur.fetchall()]
        cur.close()
        return {"t": wall(), "tm": mono(), "activity": activity, "locks": locks, "xids": xids}

    # -- queries used by protocols ----------------------------------------
    def wait_blocked(self, blocked_pid: int, blocking_pid: int,
                     timeout: float = SYNC_TIMEOUT, since: float | None = None):
        """Wait until PostgreSQL reports blocked_pid blocked by blocking_pid.

        ``since`` (monotonic) excludes samples captured before the current
        repetition started: PostgreSQL may reuse backend PIDs between
        connections, so pid-only matching could return a stale sample from a
        previous scenario.
        """

        def predicate():
            with self._cond:
                for sample in reversed(self._samples):
                    if since is not None and sample["tm"] < since:
                        continue
                    act = sample["activity"].get(blocked_pid)
                    if act and blocking_pid in act["blockers"]:
                        return {
                            "t": sample["t"],
                            "blocked": act,
                            "blocking": sample["activity"].get(blocking_pid),
                            "xids": [x for x in sample["xids"]
                                     if x["pid"] in (blocked_pid, blocking_pid)],
                            "locks": [l for l in sample["locks"]
                                      if l["pid"] in (blocked_pid, blocking_pid)],
                        }
            return None

        return wait_until(predicate, timeout,
                          f"pid {blocked_pid} blocked by pid {blocking_pid}")

    def any_cross_blocked(self, pids: list[int], timeout: float = SYNC_TIMEOUT,
                          since: float | None = None):
        """Wait until one tracked pid blocks another tracked pid."""

        def predicate():
            with self._cond:
                for sample in reversed(self._samples):
                    if since is not None and sample["tm"] < since:
                        continue
                    for pid in pids:
                        act = sample["activity"].get(pid)
                        if act and set(act["blockers"]) & set(pids):
                            return {"t": sample["t"], "blocked": act,
                                    "xids": [x for x in sample["xids"] if x["pid"] in pids]}
            return None

        return wait_until(predicate, timeout, f"cross-block among {pids}")

    def latest_for(self, pids: list[int], since: float | None = None) -> dict | None:
        with self._cond:
            for sample in reversed(self._samples):
                if since is not None and sample["tm"] < since:
                    continue
                if any(pid in sample["activity"] for pid in pids):
                    return sample
        return None

    def evidence_window(self, pids: list[int], since: float | None = None) -> list[dict]:
        """All samples in which any tracked pid was blocked (overlap evidence).

        ``since`` (monotonic) drops samples from before the current
        repetition, because PostgreSQL reuses backend PIDs across
        connections (pid-only matching would match a previous scenario).
        """
        out = []
        with self._cond:
            for sample in self._samples:
                if since is not None and sample["tm"] < since:
                    continue
                blocked = [a for pid, a in sample["activity"].items()
                           if pid in pids and a["blockers"]]
                if blocked:
                    out.append({
                        "t": sample["t"],
                        "blocked": blocked,
                        "activity": {p: sample["activity"][p] for p in pids
                                     if p in sample["activity"]},
                        "xids": [x for x in sample["xids"] if x["pid"] in pids],
                        "locks": [l for l in sample["locks"] if l["pid"] in pids],
                    })
        return out


# ---------------------------------------------------------------------------
# Worker role thread
# ---------------------------------------------------------------------------

class RoleRunner(threading.Thread):
    """One worker: independent connection + independent Odoo Environment."""

    def __init__(self, role: str, fn, ctx: Ctx, registry, uid: int, context: dict):
        super().__init__(name=role, daemon=True)
        self.role = role
        self.fn = fn
        self.ctx = ctx
        self.registry = registry
        self.uid = uid
        self.context = context
        self.outcome = Outcome(role)
        ctx.outcomes[role] = self.outcome

    def run(self) -> None:
        from odoo import api

        o = self.outcome
        cr = None
        try:
            cr = self.registry.cursor()
            env = api.Environment(cr, self.uid, dict(self.context))
            cr.execute("SELECT pg_backend_pid()")
            o.pid = cr.fetchone()[0]
            cr.execute("SELECT pg_current_xact_id()::text")
            o.txid = cr.fetchone()[0]
            cr.execute(f"SET lock_timeout = '{LOCK_TIMEOUT}'")
            cr.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT}'")
            o.started_at, o.t_start = wall(), mono()
            o.status = "running"
            self.fn(self.ctx, env, cr, o)
            if o.workflow_error:
                cr.rollback()
                o.status = "rolled_back"
            else:
                cr.commit()
                o.status = "committed"
        except BaseException as exc:  # noqa: BLE001 - capture everything
            o.runner_error = describe(exc)
            o.status = "error"
            if cr is not None:
                try:
                    cr.rollback()
                except BaseException as rex:  # noqa: BLE001
                    o.runner_error["rollback_error"] = describe(rex)
        finally:
            o.ended_at, o.t_tend = wall(), mono()
            if cr is not None:
                try:
                    cr.close()
                except BaseException:  # noqa: BLE001
                    pass
            self.ctx.sync.set(f"{self.role}_FINISHED")


# ---------------------------------------------------------------------------
# Boot / connections
# ---------------------------------------------------------------------------

EXPECTED_DB = "amnus_test_19"
EXPECTED_DB_FILTER = "^amnus_test_19$"


def boot(config_args: list[str]):
    """Boot exactly like ``odoo shell`` (supported standalone pattern)."""
    from odoo.modules.registry import Registry
    from odoo.service import server
    from odoo.tools import config

    config.parse_config(config_args, setup_logging=True)
    verify_db_config()
    server.start(preload=[], stop=True)
    registry = Registry(config["db_name"][0])
    return registry, config


def verify_db_config() -> dict:
    """Hard safety gate: only amnus_test_19 may ever be touched."""
    from odoo.tools import config

    names = list(config["db_name"] or [])
    db_filter = config["db_filter"]
    if names != [EXPECTED_DB]:
        raise SystemExit(f"SAFETY STOP: db_name={names!r} != ['{EXPECTED_DB}']")
    if db_filter != EXPECTED_DB_FILTER:
        raise SystemExit(f"SAFETY STOP: db_filter={db_filter!r} != '{EXPECTED_DB_FILTER}'")
    return {"db_name": names, "db_filter": db_filter,
            "db_host": config["db_host"], "db_port": config["db_port"],
            "db_user": config["db_user"]}


def dsn(config) -> dict:
    return {
        "host": config["db_host"] or "127.0.0.1",
        "port": config["db_port"] or 5432,
        "user": config["db_user"],
        "password": config["db_password"],
        "dbname": EXPECTED_DB,
    }


def raw_connect(config):
    import psycopg2

    return psycopg2.connect(**dsn(config))


def check_current_db(cursor) -> dict:
    """Verify at runtime that the session is on amnus_test_19."""
    cursor.execute("SELECT current_database()")
    dbname = cursor.fetchone()[0]
    if dbname != EXPECTED_DB:
        raise SystemExit(f"SAFETY STOP: connected database is {dbname!r}")
    return {"current_database": dbname}


# ---------------------------------------------------------------------------
# Invariant checks (read-only SQL, harness ids only)
# ---------------------------------------------------------------------------

def q_rows(conn, sql: str, params: tuple = ()):
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def check_empty(conn, name: str, sql: str, params: tuple = ()) -> dict:
    rows = q_rows(conn, sql, params)
    return {"name": name, "ok": not rows, "rows": [list(r) for r in rows[:20]],
            "detail": "no violating rows" if not rows else f"{len(rows)} violating row(s)"}


def check_scalar(conn, name: str, sql: str, params: tuple = ()) -> dict:
    rows = q_rows(conn, sql, params)
    value = rows[0][0] if rows else None
    expected = rows[0][1] if rows and len(rows[0]) > 1 else True
    return {"name": name, "ok": bool(expected), "value": value,
            "detail": f"value={value}"}
