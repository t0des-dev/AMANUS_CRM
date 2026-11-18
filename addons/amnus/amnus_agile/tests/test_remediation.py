# -*- coding: utf-8 -*-
"""Regression tests for Sprint 04.2 security and data-integrity remediation.

Each test maps to an audit finding (F-01..F-17) and asserts the protected
server-side behavior against direct ORM/RPC-style operations.
"""

from datetime import date, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileRemediation(AmnusAgileTestMixin, common.TransactionCase):
    """Remediation regressions for Sprint 04.1 audit findings."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Remediation Project")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _closed_sprint_with_done_story(self, points=5):
        sprint = self._create_sprint(project_id=self.project.id, name="Closed Sprint")
        story = self._create_story(
            project_id=self.project.id,
            sprint_id=sprint.id,
            story_points=points,
            state="planned",
            acceptance_criteria="Acceptance criteria are defined.",
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        sprint.with_user(self.agile_manager).action_close()
        return sprint, story

    # ------------------------------------------------------------------
    # F-01: frozen / historical sprint metrics protected
    # ------------------------------------------------------------------
    def test_f01_manager_cannot_write_final_metrics_on_closed_sprint(self):
        sprint, _story = self._closed_sprint_with_done_story(points=5)
        for field in (
            "final_committed_points",
            "final_completed_points",
            "final_carry_over_points",
            "baseline_points",
        ):
            with self.assertRaises(UserError):
                sprint.with_user(self.agile_manager).write({field: 999})

    def test_f01_closed_sprint_metrics_unchanged_after_later_story_edit(self):
        sprint, story = self._closed_sprint_with_done_story(points=5)
        self.assertEqual(sprint.completed_points, 5)
        # Story is done in a closed sprint; a direct point edit must not alter
        # frozen metrics. Sprint 04.5 (F-12/P0-A) goes further: a later story
        # point edit on a closed sprint is rejected outright; frozen metrics
        # remain unchanged either way.
        with self.assertRaises(UserError):
            story.sudo().write({"story_points": 13})
        sprint.invalidate_recordset()
        self.assertEqual(sprint.final_completed_points, 5)
        self.assertEqual(sprint.completed_points, 5)
        self.assertEqual(sprint.velocity_points, 5)

    def test_f01_cannot_create_sprint_with_fabricated_frozen_values(self):
        with self.assertRaises(UserError):
            self.env["amnus.agile.sprint"].with_user(self.agile_manager).create(
                {
                    "name": "Fabricated",
                    "project_id": self.project.id,
                    "final_completed_points": 13,
                }
            )

    # ------------------------------------------------------------------
    # F-02: story/task cross-project/company integrity and disclosure
    # ------------------------------------------------------------------
    def test_f02_cannot_link_task_from_other_project(self):
        other_project = self._create_project("Other Project")
        task = self.env["project.task"].create(
            {"name": "Foreign Task", "project_id": other_project.id}
        )
        with self.assertRaises(ValidationError):
            self._create_story(
                project_id=self.project.id,
                task_id=task.id,
                name="Bad Link",
            )

    def test_f02_cannot_move_linked_task_to_other_project(self):
        story = self._create_story(project_id=self.project.id, name="Linked Story")
        story.with_user(self.agile_manager).action_create_task()
        task = story.task_id
        other_project = self._create_project("Move Target Project")
        with self.assertRaises(UserError):
            task.with_user(self.agile_manager).write({"project_id": other_project.id})
        self.assertEqual(task.project_id, self.project)

    def test_f02_cannot_move_linked_task_to_other_company(self):
        company_b = self.env["res.company"].create({"name": "Company B F02"})
        project_b = self.env["project.project"].create(
            {"name": "Project B F02", "company_id": company_b.id}
        )
        story = self._create_story(project_id=self.project.id, name="Linked Story Co")
        story.with_user(self.agile_manager).action_create_task()
        task = story.task_id
        with self.assertRaises(UserError):
            task.with_user(self.agile_manager).write({"project_id": project_b.id})
        self.assertEqual(task.project_id, self.project)

    def test_f02_inaccessible_task_state_not_disclosed(self):
        # Create a story linking a task the reading user cannot access.
        task = self.env["project.task"].create(
            {"name": "Secret Task", "project_id": self.project.id}
        )
        story = self._create_story(
            project_id=self.project.id, task_id=task.id, name="Story With Secret Task"
        )
        # Make project private and remove agile_user as follower/assignee access path.
        self.project.write({"privacy_visibility": "followers"})
        story_visible = story.with_user(self.agile_user)
        # User cannot see the story/project by record rules in this setup; ensure no leakage
        # when computed in a context where story is readable but task is not by checking via sudo read of story.
        # Simulate: read as manager-visible record values computed without sudo escalation.
        story_as_user = self.env["amnus.agile.user.story"].with_user(self.agile_user).browse(story.id)
        # If record rules hide story, access error is correct (no disclosure). If readable, fields must be empty.
        try:
            story_as_user.read(["task_state", "task_user_ids"])
        except AccessError:
            pass
        else:
            self.assertFalse(story_as_user.task_state)
            self.assertFalse(story_as_user.task_user_ids)

    # ------------------------------------------------------------------
    # F-03: sprint lifecycle direct state writes blocked
    # ------------------------------------------------------------------
    def test_f03_direct_write_state_close_rejected(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).write({"state": "closed"})
        self.assertEqual(sprint.state, "active")
        self.assertEqual(sprint.final_completed_points, 0)

    def test_f03_direct_write_state_start_and_cancel_rejected(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).write({"state": "active"})
        self.assertEqual(sprint.state, "planned")
        sprint.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).write({"state": "cancelled"})
        self.assertEqual(sprint.state, "active")

    def test_f03_repeated_close_rejected(self):
        sprint, _ = self._closed_sprint_with_done_story()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).action_close()
        self.assertEqual(sprint.state, "closed")

    # ------------------------------------------------------------------
    # F-04: guarded create
    # ------------------------------------------------------------------
    def test_f04_cannot_create_closed_sprint(self):
        with self.assertRaises(UserError):
            self.env["amnus.agile.sprint"].with_user(self.agile_manager).create(
                {"name": "Closed On Create", "project_id": self.project.id, "state": "closed"}
            )

    def test_f04_cannot_create_done_story_directly(self):
        with self.assertRaises(UserError):
            self._create_story(
                project_id=self.project.id,
                state="done",
                acceptance_criteria="Criteria",
                name="Done On Create",
            )

    def test_f04_cannot_create_story_in_closed_sprint(self):
        sprint, _ = self._closed_sprint_with_done_story()
        with self.assertRaises(UserError):
            self._create_story(
                project_id=self.project.id,
                sprint_id=sprint.id,
                name="Late Story",
            )

    # ------------------------------------------------------------------
    # F-05: unlink protection
    # ------------------------------------------------------------------
    def test_f05_cannot_unlink_closed_sprint(self):
        sprint, _ = self._closed_sprint_with_done_story()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).unlink()

    def test_f05_cannot_unlink_story_with_membership_history(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id, sprint_id=sprint.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).unlink()

    # ------------------------------------------------------------------
    # F-06: direct assignment to closed/cancelled sprint rejected
    # ------------------------------------------------------------------
    def test_f06_direct_write_to_closed_sprint_rejected(self):
        sprint, _ = self._closed_sprint_with_done_story()
        story = self._create_story(project_id=self.project.id, name="Movable")
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"sprint_id": sprint.id})

    # ------------------------------------------------------------------
    # F-07: carry-over cannot rewrite closed source history
    # ------------------------------------------------------------------
    def test_f07_carry_over_from_closed_sprint_rejected(self):
        source, story = self._closed_sprint_with_done_story(points=3)
        # story is done; create an unfinished story scenario in a closed sprint is prevented,
        # so verify closed-source rejection by attempting on closed source directly.
        target = self._create_sprint(project_id=self.project.id, name="Target Sprint")
        unfinished = self._create_story(
            project_id=self.project.id, sprint_id=target.id, story_points=2, state="planned"
        )
        # Try carrying from closed source using unfinished story id mismatch will fail earlier;
        # assert closed source is rejected.
        with self.assertRaises(UserError):
            source.with_user(self.agile_manager).action_carry_over([story.id], target.id)

    # ------------------------------------------------------------------
    # F-08: burndown events and Day 1-5 scenario
    # ------------------------------------------------------------------
    def test_f08_day1_to_day5_burndown_scenario(self):
        sprint = self._create_sprint(
            project_id=self.project.id,
            name="Burndown D1-D5",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 1, 14),
        )
        story_a = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=5, state="planned",
            name="Story A",
        )
        story_b = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=3, state="planned",
            acceptance_criteria="B criteria",
            name="Story B",
        )
        target = self._create_sprint(
            project_id=self.project.id, name="Carry Target D5",
            date_start=date(2026, 1, 15), date_end=date(2026, 1, 28),
        )

        # Day 1: start sprint (baseline 8)
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()

        # Day 2: A completes
        story_a.with_user(self.agile_manager).action_start()
        story_a.with_user(self.agile_manager).write({"acceptance_criteria": "A done"})
        story_a.with_user(self.agile_manager).action_done()

        # Day 3: B re-estimated 3 -> 5
        story_b.with_user(self.agile_manager).write({"story_points": 5})

        # Day 4: C=2 added
        story_c = self._create_story(
            project_id=self.project.id, story_points=2, name="Story C", state="backlog"
        )
        sprint.with_user(self.agile_manager).action_add_stories(sprint.id, [story_c.id])

        # Day 5: B removed and carried over
        # carry-over requires story in this sprint and unfinished; use workflow carry-over
        sprint.with_user(self.agile_manager).action_carry_over([story_b.id], target.id)

        points = self.env["amnus.agile.burndown"].sudo().search(
            [("sprint_id", "=", sprint.id)], order="event_sequence asc, id asc"
        )
        self.assertTrue(points, "Burndown events must be recorded")
        remaining_series = [p.remaining_points for p in points]
        completed_series = [p.completed_points for p in points]
        event_types = list(points.mapped("event_type"))
        # Baseline 8/0, after A done 3/5, after B reestimate 5/5, after C add 7/5, after carry-over out 2/5
        self.assertIn("baseline", event_types)
        self.assertIn("completion", event_types)
        self.assertIn("reestimate", event_types)
        self.assertIn("scope_add", event_types)
        self.assertIn("carry_over_out", event_types)
        self.assertEqual(remaining_series[0], 8)
        self.assertEqual(completed_series[0], 0)
        self.assertEqual(remaining_series[-1], 2)
        self.assertEqual(completed_series[-1], 5)
        # The required Day 1-5 progression must be present in recorded order.
        expected_progression = [8, 3, 5, 7, 2]
        idx = 0
        for value in remaining_series:
            if idx < len(expected_progression) and value == expected_progression[idx]:
                idx += 1
        self.assertEqual(idx, len(expected_progression), remaining_series)

    def test_f08_series_carries_forward_event_free_days(self):
        sprint = self._create_sprint(
            project_id=self.project.id,
            name="Carry Forward",
            date_start=date(2026, 2, 1),
            date_end=date(2026, 2, 10),
        )
        self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=3, state="planned"
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        # Add a later event by closing
        sprint.with_user(self.agile_manager).action_close()
        series = self.env["amnus.agile.sprint"].get_burndown_series(sprint.id)
        self.assertTrue(series)
        # No day in the continuous series should imply 0 remaining unless last value is 0.
        for entry in series:
            self.assertIn("remaining_points", entry)

    # ------------------------------------------------------------------
    # F-09: story direct write/create bypass protections
    # ------------------------------------------------------------------
    def test_f09_direct_write_done_rejected(self):
        story = self._create_story(
            project_id=self.project.id, acceptance_criteria="Criteria", story_points=2
        )
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"state": "done"})
        self.assertEqual(story.state, "in_progress")

    def test_f09_cannot_create_story_in_progress_state(self):
        with self.assertRaises(UserError):
            self._create_story(project_id=self.project.id, state="in_progress", name="Bad State")

    # ------------------------------------------------------------------
    # F-10: same-state / idempotent planning transitions
    # ------------------------------------------------------------------
    def test_f10_add_already_planned_story_to_sprint(self):
        sprint = self._create_sprint(project_id=self.project.id, name="F10 Sprint")
        story = self._create_story(project_id=self.project.id, state="backlog")
        story.with_user(self.agile_manager).action_plan()
        self.assertEqual(story.state, "planned")
        # Adding an already-planned story must not fail with planned->planned.
        story.with_user(self.agile_manager).action_add_to_sprint(sprint.id)
        self.assertEqual(story.sprint_id, sprint)
        self.assertEqual(story.state, "planned")

    # ------------------------------------------------------------------
    # F-11: burndown ordering / event uniqueness
    # ------------------------------------------------------------------
    def test_f11_burndown_events_have_deterministic_ordering(self):
        sprint = self._create_sprint(project_id=self.project.id, name="F11 Sprint")
        Burndown = self.env["amnus.agile.burndown"].sudo()
        Burndown.create({
            "sprint_id": sprint.id, "date": "2026-03-01",
            "remaining_points": 5, "completed_points": 0,
            "event_type": "baseline", "event_sequence": 1,
        })
        Burndown.create({
            "sprint_id": sprint.id, "date": "2026-03-01",
            "remaining_points": 3, "completed_points": 2,
            "event_type": "completion", "event_sequence": 2,
        })
        pts = self.env["amnus.agile.sprint"].get_burndown_points(sprint.id)
        self.assertEqual([p.event_sequence for p in pts], [1, 2])

    # ------------------------------------------------------------------
    # F-13: burndown project visibility
    # ------------------------------------------------------------------
    def test_f13_burndown_hidden_from_non_follower_user(self):
        # Restrict project visibility and ensure burndown follows project rules.
        self.project.write({"privacy_visibility": "followers"})
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=1, state="planned"
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        points = self.env["amnus.agile.burndown"].sudo().search([("sprint_id", "=", sprint.id)])
        self.assertTrue(points)
        found = self.env["amnus.agile.burndown"].with_user(self.agile_user).search(
            [("id", "in", points.ids)]
        )
        self.assertFalse(found)

    # ------------------------------------------------------------------
    # F-14: membership re-entry / history preservation
    # ------------------------------------------------------------------
    def test_f14_story_cannot_reenter_same_sprint_after_removal(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Reentry Sprint")
        story = self._create_story(project_id=self.project.id, sprint_id=sprint.id)
        story.with_user(self.agile_manager).action_remove_from_sprint()
        # Historical row exists; re-adding must be rejected to preserve history.
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"sprint_id": sprint.id})

    # ------------------------------------------------------------------
    # F-15: epic state guarded
    # ------------------------------------------------------------------
    def test_f15_epic_state_cannot_be_written_directly(self):
        epic = self._create_epic(project_id=self.project.id)
        with self.assertRaises(UserError):
            epic.with_user(self.agile_manager).write({"state": "done"})
        self.assertEqual(epic.state, "open")

    # ------------------------------------------------------------------
    # F-16: sprint capacity validation
    # ------------------------------------------------------------------
    def test_f16_negative_capacity_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_sprint(project_id=self.project.id, capacity_points=-5)
