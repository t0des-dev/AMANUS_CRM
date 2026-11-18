# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileEpic(AmnusAgileTestMixin, common.TransactionCase):
    """Epic progress derivation and lifecycle."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Agile Epic Project")

    def test_epic_progress_from_story_completion(self):
        epic = self._create_epic(project_id=self.project.id)
        first = self._create_story(
            project_id=self.project.id,
            epic_id=epic.id,
            story_points=2,
            acceptance_criteria="First story is accepted.",
        )
        second = self._create_story(
            project_id=self.project.id,
            epic_id=epic.id,
            story_points=3,
            acceptance_criteria="Second story is accepted.",
        )

        self.assertEqual(epic.story_count, 2)
        self.assertEqual(epic.completed_story_count, 0)
        self.assertEqual(epic.progress, 0.0)

        first.with_user(self.agile_manager).action_plan()
        first.with_user(self.agile_manager).action_start()
        first.with_user(self.agile_manager).action_done()
        self.assertEqual(epic.completed_story_count, 1)
        self.assertEqual(epic.progress, 50.0)

        second.with_user(self.agile_manager).action_plan()
        second.with_user(self.agile_manager).action_start()
        second.with_user(self.agile_manager).action_done()
        self.assertEqual(epic.completed_story_count, 2)
        self.assertEqual(epic.progress, 100.0)

    def test_epic_without_stories_has_zero_progress(self):
        epic = self._create_epic(project_id=self.project.id)
        self.assertEqual(epic.story_count, 0)
        self.assertEqual(epic.completed_story_count, 0)
        self.assertEqual(epic.progress, 0.0)

    def test_epic_action_done(self):
        epic = self._create_epic(project_id=self.project.id)
        epic.with_user(self.agile_manager).action_done()
        self.assertEqual(epic.state, "done")

    def test_epic_action_done_invalid_state(self):
        epic = self._create_epic(project_id=self.project.id)
        epic.with_user(self.agile_manager).action_done()
        with self.assertRaises(UserError):
            epic.with_user(self.agile_manager).action_done()

    def test_epic_action_manager_only(self):
        epic = self._create_epic(project_id=self.project.id)
        with self.assertRaises(UserError):
            epic.with_user(self.agile_user).action_done()
