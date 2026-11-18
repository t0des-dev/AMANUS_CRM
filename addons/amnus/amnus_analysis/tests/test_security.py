# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from .common import AmnusAnalysisTestMixin


@tagged("standard", "amnus_analysis", "at_install", "-post_install")
class TestAmnusAnalysisSecurity(AmnusAnalysisTestMixin, common.TransactionCase):
    """AMNUS Analysis group hierarchy, ACLs, record rules and cross-company isolation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Analysis Security Project")

    def test_group_hierarchy(self):
        self.assertTrue(self.analysis_user.has_group("amnus_analysis.group_amnus_analysis_user"))
        self.assertTrue(self.analysis_manager.has_group("amnus_analysis.group_amnus_analysis_manager"))
        self.assertTrue(self.analysis_admin.has_group("amnus_analysis.group_amnus_analysis_admin"))
        self.assertTrue(self.analysis_user.has_group("amnus_core.group_amnus_user"))
        self.assertTrue(self.analysis_manager.has_group("amnus_analysis.group_amnus_analysis_user"))
        self.assertTrue(self.analysis_manager.has_group("amnus_projects.group_amnus_project_manager"))
        self.assertTrue(self.analysis_admin.has_group("amnus_analysis.group_amnus_analysis_manager"))

    def test_analysis_groups_are_not_auto_assigned(self):
        user = self.env["res.users"].create(
            {
                "name": "Plain Analysis User",
                "login": "plain_analysis_user_test",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertFalse(user.has_group("amnus_analysis.group_amnus_analysis_user"))

    def test_analysis_user_acls(self):
        requirement_model = self.env["amnus.analysis.requirement"].with_user(self.analysis_user)
        self.assertTrue(requirement_model.has_access("read"))
        self.assertTrue(requirement_model.has_access("create"))
        self.assertTrue(requirement_model.has_access("write"))
        self.assertFalse(requirement_model.has_access("unlink"))

        workshop_model = self.env["amnus.analysis.workshop"].with_user(self.analysis_user)
        self.assertTrue(workshop_model.has_access("create"))

        process_model = self.env["amnus.analysis.process"].with_user(self.analysis_user)
        self.assertTrue(process_model.has_access("create"))

    def test_analysis_manager_acls(self):
        requirement_model = self.env["amnus.analysis.requirement"].with_user(self.analysis_manager)
        self.assertTrue(requirement_model.has_access("create"))
        self.assertTrue(requirement_model.has_access("write"))
        self.assertTrue(requirement_model.has_access("unlink"))

    def test_user_cannot_write_state_directly(self):
        requirement = self._create_requirement(self.project, name="Security Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_manager).write({"state": "approved"})

    def test_user_cannot_approve(self):
        requirement = self._create_requirement(self.project, name="Approval Security")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        with self.assertRaises(UserError):
            requirement.with_user(self.analysis_user).action_approve()

    def test_manager_can_approve(self):
        requirement = self._create_requirement(self.project, name="Manager Approve")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        self.assertEqual(requirement.state, "approved")

    def test_cross_company_requirement_is_hidden(self):
        company_a = self.env["res.company"].create({"name": "Analysis Company A"})
        company_b = self.env["res.company"].create({"name": "Analysis Company B"})
        project_a = self._create_project("Analysis Company A Project", company_id=company_a.id)
        requirement_a = self._create_requirement(project_a, name="Company A Requirement")

        user_b = self.env["res.users"].create(
            {
                "name": "Analysis Company B User",
                "login": "analysis_company_b_user_test",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.analysis_user_group.id])],
            }
        )

        requirement_b_model = self.env["amnus.analysis.requirement"].with_user(user_b)
        requirements_b = requirement_b_model.search([("id", "=", requirement_a.id)])
        self.assertEqual(len(requirements_b), 0)

    def test_user_sees_own_project_requirements(self):
        requirement = self._create_requirement(self.project, name="Visible Requirement")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        visible = self.env["amnus.analysis.requirement"].with_user(self.analysis_user).search([])
        self.assertTrue(any(r.id == requirement.id for r in visible))

    def test_version_model_readonly_for_all(self):
        version_model = self.env["amnus.analysis.requirement.version"].with_user(self.analysis_user)
        self.assertTrue(version_model.has_access("read"))
        self.assertFalse(version_model.has_access("create"))
        self.assertFalse(version_model.has_access("write"))
        self.assertFalse(version_model.has_access("unlink"))

        version_model_mgr = self.env["amnus.analysis.requirement.version"].with_user(self.analysis_manager)
        self.assertTrue(version_model_mgr.has_access("read"))
        self.assertFalse(version_model_mgr.has_access("create"))
        self.assertFalse(version_model_mgr.has_access("write"))
        self.assertFalse(version_model_mgr.has_access("unlink"))

    def test_version_immutable_at_orm_level(self):
        requirement = self._create_requirement(self.project, name="ORM Immutable")
        requirement.with_user(self.analysis_user).action_submit_for_review()
        requirement.with_user(self.analysis_manager).action_approve()
        version = requirement.version_ids[0]
        with self.assertRaises(UserError):
            version.with_user(self.analysis_manager).write({"name": "Hacked"})
        with self.assertRaises(UserError):
            version.with_user(self.analysis_manager).unlink()

    def test_version_cannot_be_created_directly(self):
        requirement = self._create_requirement(self.project, name="Direct Create")
        with self.assertRaises(UserError):
            self.env["amnus.analysis.requirement.version"].with_user(self.analysis_user).create(
                {"requirement_id": requirement.id, "version_number": 99, "name": "Fake"}
            )
