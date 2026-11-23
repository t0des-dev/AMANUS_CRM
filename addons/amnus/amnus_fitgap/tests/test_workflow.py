# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common, tagged

from .common import AmnusFitgapTestMixin


@tagged("standard", "amnus_fitgap", "at_install", "-post_install")
class TestAmnusFitgapWorkflow(AmnusFitgapTestMixin, common.TransactionCase):
    """Assessment workflow tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Workflow Test Project")

    def _make_under_review(self, name="Workflow Assessment"):
        requirement = self._create_approved_requirement(self.project, name=f"Req {name}")
        assessment = self._create_assessment(requirement, name=name)
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        return requirement, assessment

    def test_full_approval(self):
        requirement, assessment = self._make_under_review("Approve")
        assessment.with_user(self.fitgap_manager).action_approve()
        self.assertEqual(assessment.state, "approved")
        self.assertTrue(assessment.is_current)
        self.assertEqual(assessment.approved_by, self.fitgap_manager)
        self.assertTrue(assessment.version_ids)
        self.assertEqual(assessment.current_version, 1)

    def test_approval_requires_manager(self):
        requirement, assessment = self._make_under_review("User Approve")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_user).action_approve()

    def test_rejection_requires_reason(self):
        requirement, assessment = self._make_under_review("Reject")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).action_reject()
        assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="Not viable")
        self.assertEqual(assessment.state, "rejected")
        self.assertEqual(assessment.rejection_reason, "Not viable")
        self.assertFalse(assessment.is_current)

    def test_invalid_transitions(self):
        requirement, assessment = self._make_under_review("Invalid")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).action_start_analysis()
        # approve then cannot reject
        assessment.with_user(self.fitgap_manager).action_approve()
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="late")

    def test_direct_state_write_rejected(self):
        requirement, assessment = self._make_under_review("Direct")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"state": "approved"})

    def test_approved_content_immutable(self):
        requirement, assessment = self._make_under_review("Immutable")
        assessment.with_user(self.fitgap_manager).action_approve()
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"name": "Changed"})
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"development_effort": 99.0})

    def test_approved_estimation_immutable(self):
        requirement, assessment = self._make_under_review("Estimate")
        assessment.with_user(self.fitgap_manager).write({"development_effort": 5.0})
        # already under review
        assessment.with_user(self.fitgap_manager).action_approve()
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"development_effort": 10.0})

    def test_cancel(self):
        requirement = self._create_approved_requirement(self.project, name="Req Cancel")
        assessment = self._create_assessment(requirement, name="Cancel")
        assessment.with_user(self.fitgap_user).action_cancel()
        self.assertEqual(assessment.state, "cancelled")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_user).write({"name": "Changed"})

    def test_revision_creates_candidate(self):
        requirement, assessment = self._make_under_review("Revise")
        assessment.with_user(self.fitgap_manager).action_approve()
        self.assertTrue(assessment.is_current)
        assessment.with_user(self.fitgap_manager).action_request_revision()
        # original remains approved and current
        self.assertEqual(assessment.state, "approved")
        self.assertTrue(assessment.is_current)
        candidates = self.env["amnus.fitgap.assessment"].search(
            [("requirement_id", "=", requirement.id), ("is_current", "=", False)]
        )
        self.assertTrue(candidates)
        self.assertEqual(candidates[0].state, "draft")

    def test_replacement_approval_supersedes_previous(self):
        requirement = self._create_approved_requirement(self.project, name="Req Replace")
        first = self._create_assessment(requirement, name="First")
        first.with_user(self.fitgap_user).action_start_analysis()
        first.with_user(self.fitgap_user).action_submit_for_review()
        first.with_user(self.fitgap_manager).action_approve()
        self.assertTrue(first.is_current)

        second = self._create_assessment(requirement, name="Second")
        second.with_user(self.fitgap_user).action_start_analysis()
        second.with_user(self.fitgap_user).action_submit_for_review()
        second.with_user(self.fitgap_manager).action_approve()

        first.invalidate_recordset()
        second.invalidate_recordset()
        self.assertEqual(first.state, "superseded")
        self.assertFalse(first.is_current)
        self.assertEqual(second.state, "approved")
        self.assertTrue(second.is_current)

    def test_rejected_candidate_leaves_current(self):
        requirement = self._create_approved_requirement(self.project, name="Req Reject Candidate")
        first = self._create_assessment(requirement, name="First")
        first.with_user(self.fitgap_user).action_start_analysis()
        first.with_user(self.fitgap_user).action_submit_for_review()
        first.with_user(self.fitgap_manager).action_approve()

        candidate = self._create_assessment(requirement, name="Candidate")
        candidate.with_user(self.fitgap_user).action_start_analysis()
        candidate.with_user(self.fitgap_user).action_submit_for_review()
        candidate.with_user(self.fitgap_manager).action_reject(rejection_reason="No")
        first.invalidate_recordset()
        self.assertTrue(first.is_current)
        self.assertEqual(first.state, "approved")

    def test_cancelled_candidate_leaves_current(self):
        requirement = self._create_approved_requirement(self.project, name="Req Cancel Candidate")
        first = self._create_assessment(requirement, name="First")
        first.with_user(self.fitgap_user).action_start_analysis()
        first.with_user(self.fitgap_user).action_submit_for_review()
        first.with_user(self.fitgap_manager).action_approve()

        candidate = self._create_assessment(requirement, name="Candidate")
        candidate.with_user(self.fitgap_user).action_cancel()
        first.invalidate_recordset()
        self.assertTrue(first.is_current)
        self.assertEqual(first.state, "approved")

    def test_current_unique_index(self):
        requirement = self._create_approved_requirement(self.project, name="Req Unique")
        a1 = self._create_assessment(requirement, name="A1")
        a1.with_user(self.fitgap_user).action_start_analysis()
        a1.with_user(self.fitgap_user).action_submit_for_review()
        a1.with_user(self.fitgap_manager).action_approve()
        # manually attempt to set a second current assessment
        a2 = self._create_assessment(requirement, name="A2")
        with self.assertRaises(Exception):
            a2.sudo().write({"is_current": True})

    def test_concurrent_approval_not_duplicate_current(self):
        # Sequential equivalent: two candidates cannot both be current.
        requirement = self._create_approved_requirement(self.project, name="Req Concurrent")
        a = self._create_assessment(requirement, name="A")
        b = self._create_assessment(requirement, name="B")
        a.with_user(self.fitgap_user).action_start_analysis()
        a.with_user(self.fitgap_user).action_submit_for_review()
        b.with_user(self.fitgap_user).action_start_analysis()
        b.with_user(self.fitgap_user).action_submit_for_review()
        a.with_user(self.fitgap_manager).action_approve()
        # A second candidate can still be approved; it supersedes the first.
        b.with_user(self.fitgap_manager).action_approve()
        a.invalidate_recordset()
        b.invalidate_recordset()
        self.assertEqual(a.state, "superseded")
        self.assertEqual(b.state, "approved")
        self.assertFalse(a.is_current)
        self.assertTrue(b.is_current)


    def test_requirement_id_protected_on_finalized(self):
        requirement = self._create_approved_requirement(self.project, name="Req Protect")
        assessment = self._create_assessment(requirement, name="Protect")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="No")
        other_requirement = self._create_approved_requirement(self.project, name="Other Req")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"requirement_id": other_requirement.id})

    def test_requirement_id_protected_approved(self):
        requirement, assessment = self._make_under_review("Protect Approved")
        assessment.with_user(self.fitgap_manager).action_approve()
        other_requirement = self._create_approved_requirement(self.project, name="Other Approved Req")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"requirement_id": other_requirement.id})

    def test_requirement_id_protected_cancelled(self):
        requirement = self._create_approved_requirement(self.project, name="Req Cancel Protect")
        assessment = self._create_assessment(requirement, name="Cancel Protect")
        assessment.with_user(self.fitgap_user).action_cancel()
        other_requirement = self._create_approved_requirement(self.project, name="Other Cancel Req")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"requirement_id": other_requirement.id})

    def test_requirement_id_protected_superseded(self):
        requirement = self._create_approved_requirement(self.project, name="Req Supersede Protect")
        first = self._create_assessment(requirement, name="First Protect")
        first.with_user(self.fitgap_user).action_start_analysis()
        first.with_user(self.fitgap_user).action_submit_for_review()
        first.with_user(self.fitgap_manager).action_approve()
        second = self._create_assessment(requirement, name="Second Protect")
        second.with_user(self.fitgap_user).action_start_analysis()
        second.with_user(self.fitgap_user).action_submit_for_review()
        second.with_user(self.fitgap_manager).action_approve()
        first.invalidate_recordset()
        other_requirement = self._create_approved_requirement(self.project, name="Other Supersede Req")
        with self.assertRaises(UserError):
            first.with_user(self.fitgap_manager).write({"requirement_id": other_requirement.id})

    def test_reference_immutable(self):
        requirement = self._create_approved_requirement(self.project, name="Req Ref")
        assessment = self._create_assessment(requirement, name="Ref")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).write({"reference": "FG-99999"})

    def test_rejection_via_record_reason(self):
        requirement, assessment = self._make_under_review("Reject Via Field")
        assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="Not suitable")
        self.assertEqual(assessment.state, "rejected")
        self.assertEqual(assessment.rejection_reason, "Not suitable")

    def test_rejection_empty_reason_rejected(self):
        requirement, assessment = self._make_under_review("Reject Empty")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="   ")

    def test_rejection_unauthorized(self):
        requirement, assessment = self._make_under_review("Reject Unauthorized")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_user).action_reject(rejection_reason="No")

    def test_rejection_invalid_state(self):
        requirement = self._create_approved_requirement(self.project, name="Req Reject State")
        assessment = self._create_assessment(requirement, name="Reject State")
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_manager).action_reject(rejection_reason="No")


    def test_multi_record_requirement_id_protected(self):
        requirement = self._create_approved_requirement(self.project, name="Req Multi")
        a1 = self._create_assessment(requirement, name="A1 Multi")
        a2 = self._create_assessment(requirement, name="A2 Multi")
        a1.with_user(self.fitgap_user).action_start_analysis()
        a1.with_user(self.fitgap_user).action_submit_for_review()
        a2.with_user(self.fitgap_user).action_start_analysis()
        a2.with_user(self.fitgap_user).action_submit_for_review()
        a1.with_user(self.fitgap_manager).action_approve()
        a2.with_user(self.fitgap_manager).action_reject(rejection_reason="No")
        other_requirement = self._create_approved_requirement(self.project, name="Other Multi Req")
        with self.assertRaises(UserError):
            (a1 | a2).with_user(self.fitgap_manager).write({"requirement_id": other_requirement.id})


    def test_reject_wizard_opens(self):
        requirement, assessment = self._make_under_review("Reject Wizard Open")
        action = assessment.with_user(self.fitgap_manager).action_open_reject_wizard()
        self.assertEqual(action["res_model"], "amnus.fitgap.assessment.reject.wizard")
        self.assertEqual(action["target"], "new")

    def test_reject_wizard_confirms(self):
        requirement, assessment = self._make_under_review("Reject Wizard Confirm")
        wizard = self.env["amnus.fitgap.assessment.reject.wizard"].create(
            {"assessment_id": assessment.id, "rejection_reason": "Wizard reason"}
        )
        wizard.with_user(self.fitgap_manager).action_confirm()
        self.assertEqual(assessment.state, "rejected")
        self.assertEqual(assessment.rejection_reason, "Wizard reason")
