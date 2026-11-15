# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileUserStory(AmnusAgileTestMixin, common.TransactionCase):
    """Backlog user story lifecycle, constraints and sprint assignment."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Agile Story Project")

    # ------------------------------------------------------------------
    # Creation and constraints
    # ------------------------------------------------------------------
    def test_create_story_required_name(self):
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env["amnus.agile.user.story"].create({"project_id": self.project.id})

    def test_story_defaults(self):
        story = self._create_story(project_id=self.project.id)
        self.assertEqual(story.state, "backlog")
        self.assertEqual(story.company_id, self.project.company_id)
        self.assertTrue(story.active)

    def test_story_points_must_be_fibonacci(self):
        story = self._create_story(project_id=self.project.id, story_points=3)
        self.assertEqual(story.story_points, 3)
        with self.assertRaises(ValidationError):
            self._create_story(
                project_id=self.project.id, story_points=4, name="Invalid Points"
            )

    def test_linked_task_must_belong_to_same_project(self):
        task = self.env["project.task"].create(
            {
                "name": "Foreign Task",
                "project_id": self._create_project("Other Agile Task Project").id,
            }
        )
        with self.assertRaises(ValidationError):
            self._create_story(
                project_id=self.project.id, task_id=task.id, name="Cross Project Story"
            )

    def test_epic_must_belong_to_same_project(self):
        epic = self._create_epic(project_id=self.project.id)
        other_epic = self._create_epic(
            project_id=self._create_project("Other Agile Epic Project").id
        )
        with self.assertRaises(ValidationError):
            self._create_story(
                project_id=self.project.id, epic_id=other_epic.id, name="Wrong Epic Story"
            )
        self._create_story(project_id=self.project.id, epic_id=epic.id)

    def test_sprint_must_belong_to_same_project(self):
        sprint = self._create_sprint(project_id=self.project.id)
        other_sprint = self._create_sprint(
            project_id=self._create_project("Other Agile Sprint Project").id
        )
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(ValidationError):
            story.sudo().write({"sprint_id": other_sprint.id})
        story.sudo().write({"sprint_id": sprint.id})

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def test_backlog_to_planned_transition(self):
        story = self._create_story(project_id=self.project.id)
        story.with_user(self.agile_manager).action_plan()
        self.assertEqual(story.state, "planned")

    def test_planned_to_in_progress_transition(self):
        story = self._create_story(project_id=self.project.id)
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        self.assertEqual(story.state, "in_progress")

    def test_in_progress_to_done_transition(self):
        story = self._create_story(
            project_id=self.project.id, acceptance_criteria="All criteria met."
        )
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_done()
        self.assertEqual(story.state, "done")

    def test_done_requires_acceptance_criteria(self):
        story = self._create_story(project_id=self.project.id, story_points=2)
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_done()

    def test_invalid_transition_is_rejected(self):
        story = self._create_story(
            project_id=self.project.id, acceptance_criteria="All criteria met."
        )
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_start()  # cannot start from backlog
        story.with_user(self.agile_manager).action_plan()
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_done()  # cannot finish from planned
        story.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).write({"state": "planned"})  # backward move rejected
        story.with_user(self.agile_manager).action_done()
        self.assertEqual(story.state, "done")

    def test_cancel_from_in_progress(self):
        story = self._create_story(project_id=self.project.id)
        story.with_user(self.agile_manager).action_plan()
        story.with_user(self.agile_manager).action_start()
        story.with_user(self.agile_manager).action_cancel()
        self.assertEqual(story.state, "cancelled")

    def test_user_cannot_change_story_state(self):
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).action_plan()

    # ------------------------------------------------------------------
    # Sprint assignment
    # ------------------------------------------------------------------
    def test_add_and_remove_story_from_sprint(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id)
        story.with_user(self.agile_manager).action_add_to_sprint(sprint.id)
        self.assertEqual(story.sprint_id, sprint)
        self.assertEqual(story.state, "planned")
        story.with_user(self.agile_manager).action_remove_from_sprint()
        self.assertFalse(story.sprint_id)

    def test_add_to_closed_sprint_is_rejected(self):
        sprint = self._create_sprint(project_id=self.project.id)
        sprint.with_user(self.agile_manager).action_plan()
        sprint.with_user(self.agile_manager).action_start()
        sprint.with_user(self.agile_manager).action_close()
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_add_to_sprint(sprint.id)

    # ------------------------------------------------------------------
    # Task linkage and membership protection
    # ------------------------------------------------------------------
    def test_task_can_only_link_to_one_story(self):
        task = self.env["project.task"].create(
            {"name": "Shared Execution Task", "project_id": self.project.id}
        )
        self._create_story(project_id=self.project.id, task_id=task.id, name="First Story")
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._create_story(
                project_id=self.project.id, task_id=task.id, name="Second Story"
            )

    def test_manager_can_create_execution_task(self):
        story = self._create_story(project_id=self.project.id)
        story.with_user(self.agile_manager).action_create_task()
        self.assertTrue(story.task_id)
        self.assertEqual(story.task_id.project_id, self.project)
        with self.assertRaises(UserError):
            story.with_user(self.agile_manager).action_create_task()

    def test_user_cannot_change_sprint_membership(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).write({"sprint_id": sprint.id})
        self.assertFalse(story.sprint_id)

    def test_defaults_include_optional_planning_metadata(self):
        story = self._create_story(project_id=self.project.id)
        self.assertFalse(story.business_value)
        self.assertFalse(story.tag_ids)
