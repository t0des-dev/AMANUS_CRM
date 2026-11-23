# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from .common import AmnusFitgapTestMixin


@tagged("standard", "amnus_fitgap", "at_install", "-post_install")
class TestAmnusFitgapSecurity(AmnusFitgapTestMixin, common.TransactionCase):
    """Security, ACLs, record rules and attachment visibility."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Security Test Project")

    def test_group_hierarchy(self):
        self.assertTrue(self.fitgap_user.has_group("amnus_fitgap.group_amnus_fitgap_user"))
        self.assertTrue(self.fitgap_manager.has_group("amnus_fitgap.group_amnus_fitgap_manager"))
        self.assertTrue(self.fitgap_admin.has_group("amnus_fitgap.group_amnus_fitgap_admin"))
        self.assertTrue(self.fitgap_user.has_group("amnus_core.group_amnus_user"))
        self.assertTrue(self.fitgap_manager.has_group("amnus_fitgap.group_amnus_fitgap_user"))
        self.assertTrue(self.fitgap_manager.has_group("amnus_analysis.group_amnus_analysis_manager"))
        self.assertTrue(self.fitgap_admin.has_group("amnus_fitgap.group_amnus_fitgap_manager"))

    def test_groups_not_auto_assigned(self):
        user = self.env["res.users"].create(
            {
                "name": "Plain Fit-Gap User",
                "login": "plain_fitgap_user_test",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertFalse(user.has_group("amnus_fitgap.group_amnus_fitgap_user"))

    def test_user_acls(self):
        model = self.env["amnus.fitgap.assessment"].with_user(self.fitgap_user)
        self.assertTrue(model.has_access("read"))
        self.assertTrue(model.has_access("create"))
        self.assertTrue(model.has_access("write"))
        self.assertFalse(model.has_access("unlink"))

        version_model = self.env["amnus.fitgap.assessment.version"].with_user(self.fitgap_user)
        self.assertTrue(version_model.has_access("read"))
        self.assertFalse(version_model.has_access("create"))
        self.assertFalse(version_model.has_access("write"))
        self.assertFalse(version_model.has_access("unlink"))

    def test_manager_acls(self):
        model = self.env["amnus.fitgap.assessment"].with_user(self.fitgap_manager)
        self.assertTrue(model.has_access("create"))
        self.assertTrue(model.has_access("write"))
        self.assertTrue(model.has_access("unlink"))

    def test_user_cannot_approve(self):
        requirement = self._create_approved_requirement(self.project, name="Approval Security")
        assessment = self._create_assessment(requirement, name="Security Assessment")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        with self.assertRaises(UserError):
            assessment.with_user(self.fitgap_user).action_approve()

    def test_manager_can_approve(self):
        requirement = self._create_approved_requirement(self.project, name="Manager Approve")
        assessment = self._create_assessment(requirement, name="Manager Assessment")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        assessment.with_user(self.fitgap_manager).action_approve()
        self.assertEqual(assessment.state, "approved")

    def test_cross_company_hidden(self):
        company_a = self.env["res.company"].create({"name": "FG Company A"})
        company_b = self.env["res.company"].create({"name": "FG Company B"})
        project_a = self._create_project("FG Company A Project", company_id=company_a.id)
        requirement_a = self._create_requirement(project_a, name="Company A Requirement")
        manager_a = self.env["res.users"].create(
            {
                "name": "FG Company A Manager",
                "login": "fg_company_a_manager_test",
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id])],
                "group_ids": [(6, 0, [self.fitgap_manager_group.id])],
            }
        )
        requirement_a.with_user(manager_a).action_submit_for_review()
        requirement_a.with_user(manager_a).action_approve()
        assessment_a = self._create_assessment(requirement_a, name="Company A Assessment")

        user_b = self.env["res.users"].create(
            {
                "name": "FG Company B User",
                "login": "fg_company_b_user_test",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.fitgap_user_group.id])],
            }
        )
        visible = self.env["amnus.fitgap.assessment"].with_user(user_b).search([("id", "=", assessment_a.id)])
        self.assertEqual(len(visible), 0)

    def test_version_readonly(self):
        requirement = self._create_approved_requirement(self.project, name="Version Security")
        assessment = self._create_assessment(requirement, name="Versioned")
        assessment.with_user(self.fitgap_user).action_start_analysis()
        assessment.with_user(self.fitgap_user).action_submit_for_review()
        assessment.with_user(self.fitgap_manager).action_approve()
        version = assessment.version_ids[0]
        with self.assertRaises(UserError):
            version.with_user(self.fitgap_manager).write({"name": "Hacked"})
        with self.assertRaises(UserError):
            version.with_user(self.fitgap_manager).unlink()

    def test_attachment_visibility(self):
        requirement = self._create_approved_requirement(self.project, name="Attachment Security")
        assessment = self._create_assessment(requirement, name="Attachment Assessment")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "evidence.txt",
                "datas": "Zm9v",
                "res_model": "amnus.fitgap.assessment",
                "res_id": assessment.id,
                "public": False,
            }
        )
        assessment.write({"evidence_ids": [(4, attachment.id)]})
        # same company user with fitgap access can read via comodel
        att = self.env["ir.attachment"].with_user(self.fitgap_user).browse(attachment.id)
        self.assertTrue(att.exists())
        # cross-company user cannot
        company_b = self.env["res.company"].create({"name": "FG Attach Company"})
        user_b = self.env["res.users"].create(
            {
                "name": "FG Attach User B",
                "login": "fg_attach_user_b_test",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.fitgap_user_group.id])],
            }
        )
        att_b = self.env["ir.attachment"].with_user(user_b).browse(attachment.id)
        # access check should raise or not exist
        try:
            _ = att_b.read(["name"])
            readable = True
        except Exception:
            readable = False
        self.assertFalse(readable)


    def test_attachment_authorized_same_company_read(self):
        requirement = self._create_approved_requirement(self.project, name="Attach Auth")
        assessment = self._create_assessment(requirement, name="Attach Auth Assessment")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "auth.txt",
                "datas": "Zm9v",
                "res_model": "amnus.fitgap.assessment",
                "res_id": assessment.id,
            }
        )
        assessment.write({"evidence_ids": [(4, attachment.id)]})
        att = self.env["ir.attachment"].with_user(self.fitgap_user).browse(attachment.id)
        self.assertEqual(att.read(["name"])[0]["name"], "auth.txt")

    def test_attachment_unauthorized_user_denied(self):
        requirement = self._create_approved_requirement(self.project, name="Attach Unauth")
        assessment = self._create_assessment(requirement, name="Attach Unauth Assessment")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "unauth.txt",
                "datas": "Zm9v",
                "res_model": "amnus.fitgap.assessment",
                "res_id": assessment.id,
            }
        )
        assessment.write({"evidence_ids": [(4, attachment.id)]})
        plain_user = self.env["res.users"].create(
            {
                "name": "Plain Attach User",
                "login": "plain_attach_user_test",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        att = self.env["ir.attachment"].with_user(plain_user).browse(attachment.id)
        with self.assertRaises(Exception):
            att.read(["name"])

    def test_attachment_cross_company_denied(self):
        requirement = self._create_approved_requirement(self.project, name="Attach Cross")
        assessment = self._create_assessment(requirement, name="Attach Cross Assessment")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "cross.txt",
                "datas": "Zm9v",
                "res_model": "amnus.fitgap.assessment",
                "res_id": assessment.id,
            }
        )
        assessment.write({"evidence_ids": [(4, attachment.id)]})
        company_b = self.env["res.company"].create({"name": "Attach Company B"})
        user_b = self.env["res.users"].create(
            {
                "name": "Attach User B",
                "login": "attach_user_b_test",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.fitgap_user_group.id])],
            }
        )
        att = self.env["ir.attachment"].with_user(user_b).browse(attachment.id)
        with self.assertRaises(Exception):
            att.read(["name"])

    def test_attachment_unbound_read_creator_only(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "unbound.txt",
                "datas": "Zm9v",
            }
        )
        other_user = self.env["res.users"].create(
            {
                "name": "Other Unbound User",
                "login": "other_unbound_user_test",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [(6, 0, [self.fitgap_user_group.id])],
            }
        )
        att = self.env["ir.attachment"].with_user(other_user).browse(attachment.id)
        with self.assertRaises(Exception):
            att.read(["name"])
