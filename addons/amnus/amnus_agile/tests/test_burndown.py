# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileBurndown(AmnusAgileTestMixin, common.TransactionCase):
    """Burndown point recording and velocity reporting."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Agile Burndown Project")

    def test_burndown_baseline_recorded_on_sprint_start(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Sprint Burndown")
        story = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=3, state="planned"
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()

        points = self.env["amnus.agile.burndown"].sudo().search([
            ("sprint_id", "=", sprint.id),
        ], order="date asc")
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].date, sprint.date_start)
        self.assertEqual(points[0].remaining_points, 3)
        self.assertEqual(points[0].completed_points, 0)

    def test_burndown_final_point_recorded_on_close(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Sprint Burndown Close")
        story = self._create_story(
            project_id=self.project.id, sprint_id=sprint.id, story_points=5, state="planned",
            acceptance_criteria="Close criteria",
        )
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        sprint.with_user(self.agile_manager).action_close()

        points = self.env["amnus.agile.burndown"].sudo().search([
            ("sprint_id", "=", sprint.id),
        ], order="event_sequence asc, id asc")
        self.assertGreaterEqual(len(points), 2)
        self.assertEqual(points[-1].date, sprint.date_end)
        self.assertEqual(points[-1].remaining_points, 0)
        self.assertEqual(points[-1].completed_points, 5)

    def test_get_burndown_points_ordered(self):
        sprint = self._create_sprint(project_id=self.project.id, name="Sprint Burndown Order")
        first = self.env["amnus.agile.burndown"].sudo().create({
            "sprint_id": sprint.id,
            "date": "2026-01-05",
            "remaining_points": 3,
            "completed_points": 0,
        })
        second = self.env["amnus.agile.burndown"].sudo().create({
            "sprint_id": sprint.id,
            "date": "2026-01-08",
            "remaining_points": 1,
            "completed_points": 2,
        })
        burndown_points = self.env["amnus.agile.sprint"].get_burndown_points(sprint.id)
        self.assertEqual(
            list(burndown_points.ids),
            [first.id, second.id],
        )
