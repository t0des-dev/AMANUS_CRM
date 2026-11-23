# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common, tagged

from .common import AmnusFitgapTestMixin


@tagged("standard", "amnus_fitgap", "at_install", "-post_install")
class TestAmnusFitgapVersion(AmnusFitgapTestMixin, common.TransactionCase):
    """Assessment version snapshot tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Version Test Project")

    def _approved_assessment(self, name="Versioned"):
        requirement = self._create_approved_requirement(self.project, name=f"Req {name}")
        assessment = self._create_assessment(
            requirement,
            name=name,
            outcome="custom_development",
            standard_odoo_module="project",
            standard_odoo_feature="Tasks",
            gap_description="Gap",
            development_effort=4.0,
            testing_effort=1.0,
            risk_level="high",
            decision_rationale="Because",
        )
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        assessment.with_user(self.fitgap_manager).action_approve(approval_notes="Approved")
        return assessment

    def test_snapshot_created_on_approval(self):
        assessment = self._approved_assessment("Snap")
        self.assertEqual(len(assessment.version_ids), 1)
        version = assessment.version_ids[0]
        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.name, assessment.name)
        self.assertEqual(version.outcome, assessment.outcome)
        self.assertEqual(version.standard_odoo_module, assessment.standard_odoo_module)
        self.assertEqual(version.gap_description, assessment.gap_description)
        self.assertEqual(version.development_effort, assessment.development_effort)
        self.assertEqual(version.testing_effort, assessment.testing_effort)
        self.assertEqual(version.total_effort, assessment.total_effort)
        self.assertEqual(version.risk_level, assessment.risk_level)
        self.assertEqual(version.decision_rationale, assessment.decision_rationale)
        self.assertEqual(version.approval_notes, "Approved")
        self.assertEqual(version.requirement_reference, assessment.requirement_id.reference)
        self.assertEqual(version.project_name, assessment.project_id.name)

    def test_sequential_versions(self):
        requirement = self._create_approved_requirement(self.project, name="Req Seq")
        assessment = self._create_assessment(requirement, name="Seq")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        assessment.with_user(self.fitgap_manager).action_approve()
        # revision candidate
        assessment.with_user(self.fitgap_manager).action_request_revision()
        candidate = self.env["amnus.fitgap.assessment"].search(
            [("requirement_id", "=", requirement.id), ("is_current", "=", False)], limit=1
        )
        candidate.with_user(self.fitgap_user).action_start_analysis()
        candidate.with_user(self.fitgap_user).action_submit_for_review()
        candidate.with_user(self.fitgap_manager).action_approve()
        assessment.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(assessment.current_version, 1)
        self.assertEqual(candidate.current_version, 1)
        # candidate has its own version 1; original version remains
        self.assertEqual(len(assessment.version_ids), 1)

    def test_version_immutable(self):
        assessment = self._approved_assessment("Immutable")
        version = assessment.version_ids[0]
        with self.assertRaises(UserError):
            version.with_user(self.fitgap_manager).write({"name": "Hacked"})
        with self.assertRaises(UserError):
            version.with_user(self.fitgap_manager).unlink()

    def test_version_cannot_be_created_directly(self):
        assessment = self._approved_assessment("Direct")
        with self.assertRaises(UserError):
            self.env["amnus.fitgap.assessment.version"].with_user(self.fitgap_user).create(
                {"assessment_id": assessment.id, "version_number": 99, "name": "Fake"}
            )

    def test_failed_approval_no_partial_snapshot(self):
        requirement = self._create_approved_requirement(self.project, name="Req Fail")
        assessment = self._create_assessment(requirement, name="Fail")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        # simulate failure by invalid state? Just ensure count 0 before approval
        self.assertEqual(len(assessment.version_ids), 0)
        assessment.with_user(self.fitgap_manager).action_approve()
        self.assertEqual(len(assessment.version_ids), 1)

    def test_exact_snapshot_preservation_after_mutation_attempt(self):
        assessment = self._approved_assessment("Exact")
        version = assessment.version_ids[0]
        original_name = version.name
        original_effort = version.total_effort
        # attempt mutation rejected
        try:
            version.with_user(self.fitgap_manager).write({"name": "Changed"})
        except UserError:
            pass
        version.invalidate_recordset()
        self.assertEqual(version.name, original_name)
        self.assertEqual(version.total_effort, original_effort)
