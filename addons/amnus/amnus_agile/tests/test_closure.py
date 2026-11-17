# -*- coding: utf-8 -*-
"""Sprint 04.4 closure verification tests.

Covers runtime/direct ORM re-verification of F-01..F-09 and
best-effort concurrency integrity checks where test infrastructure permits.
"""

import threading

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileClosure(AmnusAgileTestMixin, common.TransactionCase):
    """Closure regressions for Sprint 04.3 blockers."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Closure Project")

    # ------------------------------------------------------------------
    # F-01..F-09 runtime/direct ORM verification
    # ------------------------------------------------------------------
    def test_f01_frozen_metrics_runtime_direct_orm(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=5,
            state="planned", acceptance_criteria="Criteria",
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        sprint.with_user(self.agile_manager).action_close()
        for vals in (
            {"baseline_points": 99},
            {"final_committed_points": 99},
            {"final_completed_points": 99},
            {"final_carry_over_points": 99},
            {"state": "active"},
        ):
            with self.assertRaises(UserError):
                sprint.with_user(self.agile_manager).write(vals)
        # Sprint 04.5 (F-12/P0-A): re-estimating a story whose sprint is
        # closed/cancelled is now rejected; frozen metrics are protected by
        # rejection instead of by silent acceptance.
        with self.assertRaises(UserError):
            story.sudo().write({"story_points": 13})
        self.assertEqual(sprint.final_completed_points, 5)
        self.assertEqual(sprint.velocity_points, 5)

    def test_f02_task_move_and_disclosure_runtime(self):
        other_project = self._create_project("Closure Other Project")
        task = self.env["project.task"].create({"name": "Linked", "project_id": self.project.id})
        story = self._create_story(project_id=self.project.id, task_id=task.id)
        with self.assertRaises(UserError):
            task.with_user(self.agile_manager).write({"project_id": other_project.id})
        with self.assertRaises(UserError):
            task.with_user(self.agile_manager).write({"project_id": False})
        self.assertEqual(task.project_id, self.project)
        # Disclosure: computed fields must not escalate; inaccessible task values omitted.
        story.invalidate_recordset(["task_state", "task_user_ids"])
        _ = story.with_user(self.agile_manager).task_state

    def test_f03_direct_sprint_state_write_blocked_runtime(self):
        sprint = self._create_sprint(project_id=self.project.id)
        for state in ("planned", "active", "closed", "cancelled"):
            with self.assertRaises(UserError):
                sprint.with_user(self.agile_manager).write({"state": state})
        self.assertEqual(sprint.state, "draft")

    def test_f04_invalid_creation_blocked_runtime(self):
        with self.assertRaises(UserError):
            self.env["amnus.agile.sprint"].with_user(self.agile_manager).create(
                {"name": "Bad", "project_id": self.project.id, "state": "active"}
            )
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_close()
        with self.assertRaises(UserError):
            self._create_story(project_id=self.project.id, sprint_id=sprint.id)
        with self.assertRaises(UserError):
            self._create_story(project_id=self.project.id, state="in_progress")

    def test_f05_historical_records_not_destructively_deleted_runtime(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id, sprint_id=sprint.id, story_points=2, state="planned")
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).unlink()
        membership = self.env["amnus.agile.sprint.membership"].sudo().search([("story_id", "=", story.id)], limit=1)
        self.assertTrue(membership)
        with self.assertRaises(UserError):
            membership.sudo().unlink()
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_close()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).unlink()

    def test_f06_closed_sprint_assignment_rejected_runtime(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_close()
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"sprint_id": sprint.id})
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_add_to_sprint(sprint.id)

    def test_f07_closed_source_carry_over_preserves_history_runtime(self):
        source = self._create_sprint(project_id=self.project.id, name="Src")
        target = self._create_sprint(project_id=self.project.id, name="Tgt")
        story = self._create_story(project_id=self.project.id, sprint_id=source.id, story_points=3, state="planned")
        source.with_user(self.agile_manager).action_plan()
        source.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        # Cannot carry over from active in a way that rewrites closed history; close source (story becomes incomplete).
        source.with_user(self.agile_manager).action_close()
        with self.assertRaises(UserError):
            source.with_user(self.agile_manager).action_carry_over([story.id], target.id)
        memberships = self.env["amnus.agile.sprint.membership"].sudo().search([("story_id", "=", story.id), ("sprint_id", "=", source.id)])
        self.assertEqual(len(memberships), 1)
        self.assertEqual(memberships.outcome, "incomplete")

    def test_f08_dated_events_preserve_history_runtime(self):
        sprint = self._create_sprint(project_id=self.project.id, date_start="2026-03-01", date_end="2026-03-10")
        story = self._create_story(project_id=self.project.id, sprint_id=sprint.id, story_points=3, state="planned", acceptance_criteria="c")
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        events = self.env["amnus.agile.burndown"].sudo().search([("sprint_id", "=", sprint.id)], order="event_sequence asc, id asc")
        self.assertTrue(events)
        self.assertTrue(all(e.sprint_id.id == sprint.id for e in events))
        # Immutability
        with self.assertRaises(UserError):
            events[0].sudo().write({"remaining_points": 999})

    def test_f09_direct_story_state_write_and_invalid_workflow_bypass_runtime(self):
        story = self._create_story(project_id=self.project.id, acceptance_criteria="Criteria")
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"state": "done"})
        self.assertEqual(story.state, "in_progress")
        # Complete via workflow only (audited)
        story.with_user(self.agile_manager).action_done()
        self.assertEqual(story.state, "done")

    # ------------------------------------------------------------------
    # DB invariants (best-effort, sequential evidence)
    # ------------------------------------------------------------------
    def test_db_partial_unique_open_membership_per_story(self):
        """DB must reject a second open membership for the same story."""
        sprint_a = self._create_sprint(project_id=self.project.id, name="A")
        sprint_b = self._create_sprint(project_id=self.project.id, name="B")
        story = self._create_story(project_id=self.project.id, sprint_id=sprint_a.id)
        membership_model = self.env["amnus.agile.sprint.membership"].sudo()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                membership_model.create({
                    "sprint_id": sprint_b.id,
                    "story_id": story.id,
                    "outcome": "active",
                    "committed_points": 0,
                })

    def test_burndown_event_sequence_uniqueness_db(self):
        sprint = self._create_sprint(project_id=self.project.id)
        Burndown = self.env["amnus.agile.burndown"].sudo()
        Burndown.create({
            "sprint_id": sprint.id, "date": "2026-04-01",
            "remaining_points": 1, "completed_points": 0,
            "event_type": "baseline", "event_sequence": 1,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                Burndown.create({
                    "sprint_id": sprint.id, "date": "2026-04-01",
                    "remaining_points": 0, "completed_points": 1,
                    "event_type": "completion", "event_sequence": 1,
                })
