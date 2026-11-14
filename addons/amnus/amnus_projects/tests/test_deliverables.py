# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from .common import AmnusProjectTestMixin


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusDeliverableWorkflow(AmnusProjectTestMixin, common.TransactionCase):
    """Deliverable lifecycle, sign-off integrity and ORM guards."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project(
            "Deliverable Project", amnus_is_amnus_project=True
        )

    def _submitted_deliverable(self, name="Deliverable"):
        deliverable = self._create_deliverable(self.project, name)
        deliverable.with_user(self.project_user).action_submit()
        return deliverable

    def test_create_deliverable_defaults(self):
        deliverable = self._create_deliverable(self.project, "Specification")
        self.assertEqual(deliverable.state, "draft")
        self.assertEqual(deliverable.company_id, self.project.company_id)
        self.assertEqual(deliverable.responsible_id, self.project_user)
        self.assertFalse(deliverable.submitted_by)
        self.assertFalse(deliverable.accepted_by)

    def test_required_name(self):
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env["amnus.project.deliverable"].create(
                {"project_id": self.project.id, "type": "document"}
            )

    def test_cannot_create_in_non_draft_state(self):
        with self.assertRaises(UserError):
            self._create_deliverable(self.project, state="accepted")

    def test_cannot_create_with_sign_off_values(self):
        with self.assertRaises(UserError):
            self._create_deliverable(
                self.project, accepted_by=self.project_manager.id
            )

    def test_submit_records_identity_and_timestamp(self):
        deliverable = self._create_deliverable(self.project, "Submittable")
        deliverable.with_user(self.project_user).action_submit()
        self.assertEqual(deliverable.state, "submitted")
        self.assertEqual(deliverable.submitted_by, self.project_user)
        self.assertTrue(deliverable.submitted_date)
        self.assertFalse(deliverable.accepted_by)

    def test_accept_records_manager_identity(self):
        deliverable = self._submitted_deliverable("Acceptable")
        deliverable.with_user(self.project_manager).action_accept()
        self.assertEqual(deliverable.state, "accepted")
        self.assertEqual(deliverable.accepted_by, self.project_manager)
        self.assertTrue(deliverable.accepted_date)

    def test_reject_requires_reason(self):
        deliverable = self._submitted_deliverable("Rejectable")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_manager).action_reject()

    def test_reject_records_reason_and_identity(self):
        deliverable = self._submitted_deliverable("Rejected")
        deliverable.with_user(self.project_manager).write(
            {"rejection_reason": "Acceptance criteria not met."}
        )
        deliverable.with_user(self.project_manager).action_reject()
        self.assertEqual(deliverable.state, "rejected")
        self.assertEqual(deliverable.rejected_by, self.project_manager)
        self.assertTrue(deliverable.rejected_date)
        self.assertEqual(
            deliverable.rejection_reason, "Acceptance criteria not met."
        )

    def test_reset_to_draft_clears_sign_off(self):
        deliverable = self._submitted_deliverable("Resettable")
        deliverable.with_user(self.project_manager).action_reset_to_draft()
        self.assertEqual(deliverable.state, "draft")
        self.assertFalse(deliverable.submitted_by)
        self.assertFalse(deliverable.submitted_date)
        self.assertFalse(deliverable.rejected_by)
        self.assertFalse(deliverable.rejection_reason)

    def test_accepted_deliverable_cannot_be_reset(self):
        deliverable = self._submitted_deliverable("Frozen")
        deliverable.with_user(self.project_manager).action_accept()
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_manager).action_reset_to_draft()

    def test_non_responsible_user_cannot_submit(self):
        deliverable = self._create_deliverable(
            self.project, "Not mine", responsible_id=self.project_manager.id
        )
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).action_submit()

    def test_project_user_cannot_accept(self):
        deliverable = self._submitted_deliverable("User cannot accept")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).action_accept()

    def test_direct_state_write_is_blocked(self):
        deliverable = self._create_deliverable(self.project, "Direct write")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).write({"state": "accepted"})
        self.assertEqual(deliverable.state, "draft")

    def test_direct_sign_off_write_is_blocked(self):
        deliverable = self._submitted_deliverable("Forged sign-off")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).write(
                {"accepted_by": self.project_user.id}
            )
        self.assertFalse(deliverable.accepted_by)

    def test_accepted_deliverable_is_immutable_for_user(self):
        deliverable = self._submitted_deliverable("Locked")
        deliverable.with_user(self.project_manager).action_accept()
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).write({"name": "Changed"})
        deliverable.with_user(self.project_manager).write({"name": "Changed"})
        self.assertEqual(deliverable.name, "Changed")

    def test_accepted_deliverable_cannot_be_unlinked(self):
        deliverable = self._submitted_deliverable("Protected")
        deliverable.with_user(self.project_manager).action_accept()
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_manager).unlink()
        self.assertTrue(deliverable.exists())

    def test_project_user_cannot_unlink_draft(self):
        deliverable = self._create_deliverable(self.project, "User unlink")
        with self.assertRaises(AccessError):
            deliverable.with_user(self.project_user).unlink()

    def test_project_cannot_change_after_submission(self):
        other_project = self._create_project("Other Deliverable Project")
        deliverable = self._submitted_deliverable("Immovable")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_manager).write(
                {"project_id": other_project.id}
            )

    def test_multi_record_transitions(self):
        deliverables = self.env["amnus.project.deliverable"]
        for index in range(3):
            deliverables |= self._create_deliverable(
                self.project, f"Batch {index}"
            )
        deliverables.with_user(self.project_manager).action_submit()
        self.assertEqual(set(deliverables.mapped("state")), {"submitted"})
        deliverables.with_user(self.project_manager).action_accept()
        self.assertEqual(set(deliverables.mapped("state")), {"accepted"})
        self.assertEqual(
            set(deliverables.mapped("accepted_by").ids),
            {self.project_manager.id},
        )

    def test_task_count(self):
        deliverable = self._create_deliverable(self.project, "With tasks")
        self.env["project.task"].create(
            {
                "name": "Task 1",
                "project_id": self.project.id,
                "amnus_deliverable_id": deliverable.id,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Task 2",
                "project_id": self.project.id,
                "amnus_deliverable_id": deliverable.id,
            }
        )
        self.assertEqual(deliverable.task_count, 2)
