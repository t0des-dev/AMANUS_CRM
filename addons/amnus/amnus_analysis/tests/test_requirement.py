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

        requirement.with_user(self.analysis_manager).action_reject(rejection_reason="Does not meet requirements.")
        self.assertEqual(requirement.state, "rejected")
        self.assertEqual(requirement.rejected_by, self.analysis_manager)
        self.assertEqual(requirement.rejection_reason, "Does not meet requirements.")

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
        if "amnus.agile.user.story" not in self.env:
            self.skipTest("amnus_agile not installed")
        story = self.env["amnus.agile.user.story"].create(
            {
                "name": "Linked Story",
                "project_id": self.project.id,
            }
        )
        # story_id field is provided by amnus_analysis_agile integration
        if "story_id" not in self.env["amnus.analysis.requirement"]._fields:
            self.skipTest("amnus_analysis_agile integration not installed")
        requirement = self._create_requirement(
            self.project, name="Story-linked Requirement", story_id=story
        )
        self.assertEqual(requirement.story_id, story)

    def test_story_cross_project_rejected(self):
        if "amnus.agile.user.story" not in self.env:
            self.skipTest("amnus_agile not installed")
        if "story_id" not in self.env["amnus.analysis.requirement"]._fields:
            self.skipTest("amnus_analysis_agile integration not installed")
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
        requirement.with_user(self.analysis_manager).action_reject(rejection_reason="Does not meet requirements.")
        self.assertEqual(requirement.state, "rejected")
        self.assertEqual(requirement.rejected_by, self.analysis_manager)
        self.assertEqual(requirement.rejection_reason, "Does not meet requirements.")
        self.assertTrue(requirement.rejected_date)

    def test_reject_requires_reason(self):
        requirement = self._create_requirement(self.project, name="Reason Required Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).action_reject(rejection_reason="")
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).action_reject(rejection_reason="   ")

    def test_approved_content_protected(self):
        requirement = self._create_requirement(self.project, name="Protected Content")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve(approval_notes="Looks good")
        self.assertEqual(requirement.state, "approved")
        self.assertEqual(requirement.approval_notes, "Looks good")
        # Content edits should be rejected
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"name": "Changed Name"})
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"description": "Changed"})
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"priority": "critical"})

    def test_project_change_on_approved_rejected(self):
        requirement = self._create_requirement(self.project, name="Project Lock Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        other_project = self._create_project("Other Project")
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"project_id": other_project.id})

    def test_approved_version_created(self):
        requirement = self._create_requirement(self.project, name="Version Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve(approval_notes="Approved")
        self.assertEqual(requirement.current_version, 1)
        self.assertEqual(len(requirement.version_ids), 1)
        version = requirement.version_ids[0]
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.name, "Version Test")
        self.assertEqual(version.approval_notes, "Approved")
        self.assertEqual(version.approved_by, self.analysis_manager)

    def test_version_immutable(self):
        requirement = self._create_requirement(self.project, name="Immutable Version")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        version = requirement.version_ids[0]
        with self.assertRaises(UserError):
            version.write({"name": "Changed"})
        with self.assertRaises(UserError):
            version.unlink()

    def test_version_created_on_revision_cycle(self):
        requirement = self._create_requirement(self.project, name="Revision Cycle")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        self.assertEqual(requirement.current_version, 1)
        original_version = requirement.version_ids[0]
        original_name = original_version.name

        # Request revision and re-approve
        requirement.with_user(self.analysis_manager).action_request_revision()
        self.assertEqual(requirement.state, "under_review")
        self.assertFalse(requirement.approved_by)
        self.assertFalse(requirement.approved_date)

        requirement.with_user(self.analysis_manager).action_approve(approval_notes="Re-approved")
        self.assertEqual(requirement.current_version, 2)
        self.assertEqual(len(requirement.version_ids), 2)

        # Original version preserved
        self.assertEqual(original_version.name, original_name)
        self.assertEqual(original_version.approval_notes, False)

    def test_cancelled_protected_from_deletion(self):
        requirement = self._create_requirement(self.project, name="Cancelled Protect")
        requirement.with_user(self.analysis_user).action_cancel()
        self.assertEqual(requirement.state, "cancelled")
        with self.assertRaises(UserError):
            requirement.unlink()

    def test_cancel_under_review_requires_manager(self):
        requirement = self._create_requirement(self.project, name="Cancel Auth Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_user).action_cancel()
        # Manager can cancel
        requirement.with_user(self.analysis_manager).action_cancel()
        self.assertEqual(requirement.state, "cancelled")

    def test_direct_state_write_rejected_on_approved(self):
        requirement = self._create_requirement(self.project, name="Direct Write Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"state": "draft"})

    def test_approval_clears_rejection_metadata(self):
        requirement = self._create_requirement(self.project, name="Clear Reject Meta")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_reject(rejection_reason="No good")
        self.assertEqual(requirement.state, "rejected")
        self.assertEqual(requirement.rejection_reason, "No good")
        # Verify approval fields are cleared after rejection
        self.assertFalse(requirement.approved_by)
        self.assertFalse(requirement.approved_date)
        self.assertFalse(requirement.approval_notes)

    def test_approval_sets_approval_metadata(self):
        requirement = self._create_requirement(self.project, name="Approval Meta Test")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve(approval_notes="Looks good")
        self.assertEqual(requirement.state, "approved")
        self.assertEqual(requirement.approved_by, self.analysis_manager)
        self.assertTrue(requirement.approved_date)
        self.assertEqual(requirement.approval_notes, "Looks good")
        self.assertFalse(requirement.rejected_by)
        self.assertFalse(requirement.rejected_date)
        self.assertFalse(requirement.rejection_reason)
