# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAnalysisTestMixin


@tagged("standard", "amnus_analysis", "at_install", "-post_install")
class TestAmnusAnalysisProcess(AmnusAnalysisTestMixin, common.TransactionCase):
    """AMNUS Analysis process model tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Process Test Project")

    def test_process_creation(self):
        process = self._create_process(
            self.project,
            name="Order-to-Cash",
            category="business",
            as_is_description="Manual order entry.",
            to_be_description="Automated Odoo order management.",
        )
        self.assertTrue(process.id)
        self.assertEqual(process.state, "draft")
        self.assertTrue(process.reference, "Reference must be generated")
        self.assertNotEqual(process.reference, "New")
        self.assertEqual(process.project_id, self.project)
        self.assertEqual(process.customer_id, self.project.partner_id)
        self.assertEqual(process.category, "business")

    def test_process_created_in_draft_only(self):
        with self.assertRaises(UserError):
            self.env["amnus.analysis.process"].create(
                {
                    "name": "Invalid state",
                    "project_id": self.project.id,
                    "state": "approved",
                }
            )

    def test_process_state_transitions(self):
        process = self._create_process(self.project, name="Lifecycle Process")
        self.assertEqual(process.state, "draft")

        process.action_submit_for_review()
        self.assertEqual(process.state, "reviewed")

        process.action_approve()
        self.assertEqual(process.state, "approved")

    def test_process_approve_requires_manager(self):
        process = self._create_process(self.project, name="Approval Test")
        process.action_submit_for_review()
        with self.assertRaises(UserError):
            process.with_user(self.analysis_user).action_approve()

    def test_process_cancel(self):
        process = self._create_process(self.project, name="Cancellable Process")
        process.action_cancel()
        self.assertEqual(process.state, "cancelled")

    def test_process_unlink_protected_when_approved(self):
        process = self._create_process(self.project, name="Protected Process")
        process.action_submit_for_review()
        process.action_approve()
        with self.assertRaises(UserError):
            process.unlink()

    def test_process_requirement_link(self):
        requirement = self._create_requirement(self.project, name="Process Requirement")
        process = self._create_process(
            self.project, name="Linked Process", requirement_ids=[(6, 0, [requirement.id])]
        )
        self.assertIn(requirement, process.requirement_ids)

    def test_process_cross_project_requirement_rejected(self):
        other_project = self._create_project("Other Project")
        requirement = self._create_requirement(other_project, name="Other Requirement")
        with self.assertRaises(ValidationError):
            self._create_process(
                self.project,
                name="Cross-project Process",
                requirement_ids=[(6, 0, [requirement.id])],
            )
