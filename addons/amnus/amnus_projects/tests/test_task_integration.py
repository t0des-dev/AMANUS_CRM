# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import AmnusProjectTestMixin


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusTaskIntegration(AmnusProjectTestMixin, common.TransactionCase):
    """Task/deliverable link and project consistency."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Task Project", amnus_is_amnus_project=True)
        self.other_project = self._create_project("Other Task Project")
        self.deliverable = self._create_deliverable(self.project, "Task Deliverable")
        self.other_deliverable = self._create_deliverable(
            self.other_project, "Other Deliverable"
        )

    def test_task_can_link_deliverable(self):
        task = self.env["project.task"].create(
            {
                "name": "Linked Task",
                "project_id": self.project.id,
                "amnus_deliverable_id": self.deliverable.id,
            }
        )
        self.assertEqual(task.amnus_deliverable_id, self.deliverable)
        self.assertIn(task, self.deliverable.task_ids)

    def test_task_without_deliverable_still_works(self):
        task = self.env["project.task"].create(
            {"name": "Standard Task", "project_id": self.project.id}
        )
        self.assertFalse(task.amnus_deliverable_id)
        self.assertEqual(task.project_id, self.project)
        self.assertTrue(task.state)
        self.assertIn("stage_id", self.env["project.task"]._fields)

    def test_deliverable_from_another_project_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["project.task"].create(
                {
                    "name": "Invalid Link",
                    "project_id": self.project.id,
                    "amnus_deliverable_id": self.other_deliverable.id,
                }
            )

    def test_changing_project_breaks_link_and_is_rejected(self):
        task = self.env["project.task"].create(
            {
                "name": "Movable Task",
                "project_id": self.project.id,
                "amnus_deliverable_id": self.deliverable.id,
            }
        )
        with self.assertRaises(ValidationError):
            task.write({"project_id": self.other_project.id})

    def test_changing_deliverable_breaks_link_and_is_rejected(self):
        task = self.env["project.task"].create(
            {
                "name": "Re-linkable Task",
                "project_id": self.project.id,
                "amnus_deliverable_id": self.deliverable.id,
            }
        )
        with self.assertRaises(ValidationError):
            task.write({"amnus_deliverable_id": self.other_deliverable.id})

    def test_consistent_relink_is_allowed(self):
        second_deliverable = self._create_deliverable(
            self.project, "Second Deliverable"
        )
        task = self.env["project.task"].create(
            {
                "name": "Consistent Task",
                "project_id": self.project.id,
                "amnus_deliverable_id": self.deliverable.id,
            }
        )
        task.write({"amnus_deliverable_id": second_deliverable.id})
        self.assertEqual(task.amnus_deliverable_id, second_deliverable)
