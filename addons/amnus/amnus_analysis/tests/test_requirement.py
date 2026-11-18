# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAnalysisTestMixin


@tagged("standard", "amnus_analysis", "at_install", "-post_install")
class TestAmnusAnalysisRequirement(AmnusAnalysisTestMixin, common.TransactionCase):
    """AMNUS Analysis requirement model tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Requirement Test Project")

    def test_requirement_creation(self):
        requirement = self._create_requirement(
            self.project,
            name="Create customer portal",
            requirement_type="functional",
            priority="high",
            acceptance_criteria="Customer can log in and view orders.",
        )
        self.assertTrue(requirement.id)
        self.assertEqual(requirement.state, "draft")
        self.assertTrue(requirement.reference, "Reference must be generated")
        self.assertNotEqual(requirement.reference, "New")
        self.assertEqual(requirement.requirement_type, "functional")
        self.assertEqual(requirement.priority, "high")
        self.assertEqual(requirement.project_id, self.project)
        self.assertEqual(requirement.customer_id, self.project.partner_id)
        self.assertEqual(requirement.company_id, self.project.company_id)

    def test_requirement_created_in_draft_only(self):
        with self.assertRaises(UserError):
            self.env["amnus.analysis.requirement"].create(
                {
                    "name": "Invalid state",
                    "project_id": self.project.id,
                    "state": "approved",
                }
            )

    def test_requirement_reference_unique(self):
        self._create_requirement(self.project, name="First Requirement")
        with self.assertRaises(Exception):
            self.env["amnus.analysis.requirement"].create(
                {
                    "name": "Duplicate Reference",
                    "project_id": self.project.id,
                    "reference": self.env["amnus.analysis.requirement"].search(
                        [("project_id", "=", self.project.id)], limit=1
                    ).reference,
                }
            )

    def test_requirement_types(self):
        for req_type in ("business", "functional", "non_functional"):
            requirement = self._create_requirement(
                self.project, name=f"{req_type} requirement", requirement_type=req_type
            )
            self.assertEqual(requirement.requirement_type, req_type)

    def test_priorities(self):
        for priority in ("critical", "high", "medium", "low"):
            requirement = self._create_requirement(
                self.project, name=f"{priority} priority", priority=priority
            )
            self.assertEqual(requirement.priority, priority)

    def test_state_transitions(self):
        requirement = self._create_requirement(self.project, name="Lifecycle Requirement")
        self.assertEqual(requirement.state, "draft")

        requirement.with_user(self.analysis_user).action_submit_for_review()
        self.assertEqual(requirement.state, "under_review")

        requirement.with_user(self.analysis_manager).action_approve()
        self.assertEqual(requirement.state, "approved")

    def test_approval_rejected_reason(self):
        requirement = self._create_requirement(self.project, name="Rejectable Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        self.assertEqual(requirement.state, "under_review")

        requirement.with_user(self.analysis_manager).action_reject()
        self.assertEqual(requirement.state, "rejected")
        self.assertEqual(requirement.rejected_by, self.analysis_manager)

    def test_direct_state_write_rejected(self):
        requirement = self._create_requirement(self.project, name="Guarded Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"state": "approved"})

    def test_controlled_revision(self):
        requirement = self._create_requirement(self.project, name="Revisable Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        self.assertEqual(requirement.state, "approved")

        requirement.with_user(self.analysis_manager).action_request_revision()
        self.assertEqual(requirement.state, "under_review")

    def test_cancel(self):
        requirement = self._create_requirement(self.project, name="Cancellable Requirement")
        requirement.with_user(self.analysis_user).action_cancel()
        self.assertEqual(requirement.state, "cancelled")

    def test_unlink_protected_when_approved(self):
        requirement = self._create_requirement(self.project, name="Protected Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        with self.assertRaises(UserError):
            requirement.unlink()

    def test_unlink_allowed_when_draft(self):
        requirement = self._create_requirement(self.project, name="Deletable Requirement")
        requirement.unlink()
        self.assertFalse(requirement.exists())

    def test_task_same_project(self):
        task = self._create_task(self.project, name="Linked Task")
        requirement = self._create_requirement(
            self.project, name="Task-linked Requirement", task_id=task
        )
        self.assertEqual(requirement.task_id, task)

    def test_task_cross_project_rejected(self):
        other_project = self._create_project("Other Project")
        task = self._create_task(other_project, name="Other Task")
        with self.assertRaises(ValidationError):
            self._create_requirement(
                self.project, name="Cross-project Task", task_id=task
            )

    def test_story_same_project(self):
        story = self.env["amnus.agile.user.story"].create(
            {
                "name": "Linked Story",
                "project_id": self.project.id,
            }
        )
        requirement = self._create_requirement(
            self.project, name="Story-linked Requirement", story_id=story
        )
        self.assertEqual(requirement.story_id, story)

    def test_story_cross_project_rejected(self):
        other_project = self._create_project("Other Project")
        story = self.env["amnus.agile.user.story"].create(
            {
                "name": "Other Story",
                "project_id": other_project.id,
            }
        )
        with self.assertRaises(ValidationError):
            self._create_requirement(
                self.project, name="Cross-project Story", story_id=story
            )

    def test_approve_requires_manager(self):
        requirement = self._create_requirement(self.project, name="Approval Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_user).action_approve()

    def test_reject_requires_reason_tracking(self):
        requirement = self._create_requirement(self.project, name="Rejection Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_reject()
        self.assertEqual(requirement.state, "rejected")
        self.assertEqual(requirement.rejected_by, self.analysis_manager)
        self.assertTrue(requirement.rejected_date)
