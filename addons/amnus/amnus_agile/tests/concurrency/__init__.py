# -*- coding: utf-8 -*-
"""Isolated multi-transaction concurrency harness for AMNUS Agile (Sprint 04.5 P0-A).

This package is intentionally NOT imported by ``tests/__init__.py``: the harness
runs as a standalone controlled process (see ``run_concurrency.py``) because
Odoo's ``--test-enable`` framework gives every test a single cursor/transaction
that is rolled back at test end and therefore cannot host two genuinely
committing, overlapping transactions.

Transaction commits/rollbacks happen ONLY inside this harness, under the policy
documented in ``docs/sprints/SPRINT_04_5_P0A_CONCURRENCY.md`` (section 5).
"""
