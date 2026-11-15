# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileSprint(AmnusAgileTestMixin, common.TransactionCase):
    """Sprint lifecycle, metrics, membership and carry-over."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Agile Sprint Project")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def test_sprint_date_must_not_precede_start(self):
        with self.assertRaises(ValidationError):
            self._create_sprint(
                project_id=self.project.id,
                date_start="2026-02-10",
                date_end="2026-02-09",
            )
        sprint = self._create_sprint(
            project_id=self.project.id, date_start="2026-02-10", date_end="2026-02-10"
        )
        self.assertEqual(sprint.date_start, date(2026, 2, 10))

    def test_sprint_draft_to_planned_to_active_to_closed(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        self.assertEqual(sprint.state, "planned")
        sprint.with_user(self.agile_manager).action_start()
        self.assertEqual(sprint.state, "active")
        sprint.with_user(self.agile_manager).action_close()
        self.assertEqual(sprint.state, "closed")

    def test_sprint_cannot_be_planned_twice(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).action_plan()

    def test_sprint_cannot_be_closed_without_active_state(self):
        sprint = self._create_sprint(project_id=self.project.id)
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).action_close()

    def test_sprint_action_manager_only(self):
        sprint = self._create_sprint(project_id=self.project.id)
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_user).action_plan()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------
    def test_sprint_metrics_committed_completed_and_carry_over(self):
        sprint = self._create_sprint(project_id=self.project.id)
        first = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=3, state="planned"
        )
        second = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=5, state="planned",
            acceptance_criteria="Done criteria",
        )
        cancelled = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=8, state="planned"
        )
        # Drive to required states through workflow where applicable.
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        second.with_user(self.agile_manager).action_start()
        second.with_user(self.agile_manager).action_done()
        cancelled.with_user(self.agile_manager).action_cancel()

        self.assertEqual(sprint.committed_points, 8)
        self.assertEqual(sprint.completed_points, 5)
        self.assertEqual(sprint.carry_over_points, 3)

    def test_sprint_velocity_from_closed_sprints(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=5, state="planned",
            acceptance_criteria="Velocity criteria",
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        sprint.with_user(self.agile_manager).action_close()
        self.assertEqual(sprint.completed_points, 5)
        self.assertEqual(self.env["amnus.agile.sprint"]._get_sprint_velocity([sprint.id]), 5.0)

    # ------------------------------------------------------------------
    # Membership and carry-over
    # ------------------------------------------------------------------
    def test_add_stories_to_sprint(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id, story_points=2)
        sprint.with_user(self.agile_manager).action_add_stories(sprint.id, [story.id])
        self.assertEqual(story.sprint_id, sprint)
        self.assertEqual(sprint.committed_points, 2)

    def test_carry_over_moves_unfinished_story(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Sprint Carry Source")
        target = self._create_sprint(project_id=self.project.id, name="Sprint Carry Target")
        story = self._create_story(
            project_id=self.project.id,
            sprint_id=sprint.id,
            state="planned",
            story_points=3,
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_carry_over([story.id], target.id)
        self.assertEqual(story.sprint_id, target)
        self.assertEqual(story.state, "planned")
        self.assertEqual(sprint.carry_over_points, 0)
        self.assertEqual(target.committed_points, 3)

    def test_carry_over_preserves_membership_history(self):
        source = self._create_sprint(project_id=self.project.id, name="Membership Source")
        target = self._create_sprint(project_id=self.project.id, name="Membership Target")
        story = self._create_story(
            project_id=self.project.id,
            sprint_id=source.id,
            state="planned",
            story_points=5,
        )
        source.with_user(self.agile_manager).action_plan()
        source.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        source.with_user(self.agile_manager).action_carry_over(
            [story.id], target.id, reason="Not finished in time"
        )
        memberships = self.env["amnus.agile.sprint.membership"].sudo().search(
            [("story_id", "=", story.id)]
        )
        source_membership = memberships.filtered(lambda m: m.sprint_id == source)
        target_membership = memberships.filtered(lambda m: m.sprint_id == target)
        self.assertEqual(len(source_membership), 1)
        self.assertEqual(len(target_membership), 1)
        self.assertEqual(source_membership.outcome, "carried_over")
        self.assertEqual(source_membership.carry_over_sprint_id, target)
        self.assertEqual(source_membership.committed_points, 5)
        self.assertEqual(source_membership.reason, "Not finished in time")
        self.assertEqual(target_membership.outcome, "active")

    def test_carry_over_target_must_match_project(self):
        source = self._create_sprint(project_id=self.project.id, name="Carry Project Source")
        other_sprint = self._create_sprint(
            project_id=self._create_project("Carry Foreign Project").id,
            name="Carry Foreign Target",
        )
        story = self._create_story(
            project_id=self.project.id, sprint_id=source.id, state="planned"
        )
        source.with_user(self.agile_manager).action_plan()
        source.with_user(self.agile_manager).action_start()
        with self.assertRaises(ValidationError):
            source.with_user(self.agile_manager).action_carry_over(
                [story.id], other_sprint.id
            )

    # ------------------------------------------------------------------
    # Historical stability and lifecycle guards
    # ------------------------------------------------------------------
    def test_closed_sprint_metrics_are_frozen(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Frozen Sprint")
        story = self._create_story(
            project_id=self.project.id,
            sprint_id=sprint.id,
            story_points=3,
            state="planned",
            acceptance_criteria="Freeze criteria",
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        sprint.with_user(self.agile_manager).action_close()
        self.assertEqual(sprint.completed_points, 3)
        story.with_user(self.agile_manager).write({"story_points": 8})
        self.assertEqual(sprint.completed_points, 3)
        self.assertEqual(sprint.velocity_points, 3)
        self.assertEqual(
            self.env["amnus.agile.sprint"]._get_sprint_velocity([sprint.id]), 3.0
        )

    def test_closed_sprint_cannot_be_reopened(self):
        sprint = self._create_sprint(project_id=self.project.id, name="No Reopen")
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_close()
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).write({"state": "active"})

    def test_sprint_project_cannot_change_with_stories(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Project Guard")
        self._create_story(project_id=self.project.id, sprint_id=sprint.id)
        other_project = self._create_project("Sprint Other Project")
        with self.assertRaises(UserError):
            sprint.with_user(self.agile_manager).write({"project_id": other_project.id})

    def test_review_and_retrospective_fields_are_stored(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Review Sprint")
        sprint.with_user(self.agile_manager).write({
            "review_summary": "Delivered the billing increment.",
            "review_accepted_outcomes": "Invoice export accepted.",
            "review_incomplete_work": "Payment reminder postponed.",
            "retrospective_observations": "Team collaboration improved.",
            "retro_went_well": "Daily alignment.",
            "retro_did_not_go_well": "Late acceptance criteria.",
            "improvement_actions": "Refine stories before planning.",
            "action_owner_id": self.agile_manager.id,
            "action_target_date": "2026-02-28",
        })
        self.assertEqual(sprint.review_summary, "Delivered the billing increment.")
        self.assertEqual(sprint.action_owner_id, self.agile_manager)
        self.assertEqual(sprint.action_target_date.isoformat(), "2026-02-28")

    def test_membership_history_is_read_only(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Read Only Membership")
        story = self._create_story(project_id=self.project.id, sprint_id=sprint.id)
        membership = self.env["amnus.agile.sprint.membership"].sudo().search(
            [("story_id", "=", story.id)], limit=1
        )
        self.assertTrue(membership)
        with self.assertRaises(UserError), self.env.cr.savepoint():
            membership.with_user(self.agile_manager).write({"outcome": "removed"})
