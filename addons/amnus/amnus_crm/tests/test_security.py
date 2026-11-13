# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("standard", "amnus_crm", "at_install", "-post_install")
class TestAmnusCrmSecurity(common.TransactionCase):
    """Tests for AMNUS CRM security."""

    def test_user_permissions(self):
        user = self.env["res.users"].create(
            {
                "name": "CRM User",
                "login": "crm_user_test",
                "group_ids": [(6, 0, [self.env.ref("amnus_core.group_amnus_user").id])],
            }
        )
        request_model = self.env["amnus.crm.project.request"].with_user(user)
        self.assertTrue(request_model.has_access("read"))
        self.assertTrue(request_model.has_access("create"))
        self.assertTrue(request_model.has_access("write"))
        self.assertFalse(request_model.has_access("unlink"))

    def test_manager_permissions(self):
        manager = self.env["res.users"].create(
            {
                "name": "CRM Manager",
                "login": "crm_manager_test",
                "group_ids": [(6, 0, [self.env.ref("amnus_core.group_amnus_manager").id])],
            }
        )
        request_model = self.env["amnus.crm.project.request"].with_user(manager)
        self.assertTrue(request_model.has_access("read"))
        self.assertTrue(request_model.has_access("create"))
        self.assertTrue(request_model.has_access("write"))
        self.assertTrue(request_model.has_access("unlink"))

    def test_unauthorized_approval(self):
        from odoo.exceptions import UserError

        user = self.env["res.users"].create(
            {
                "name": "CRM User2",
                "login": "crm_user2_test",
                "group_ids": [(6, 0, [self.env.ref("amnus_core.group_amnus_user").id])],
            }
        )
        lead = self.env["crm.lead"].create({"name": "Auth Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        request.action_submit()

        with self.assertRaises(UserError):
            request.with_user(user).action_approve()

    def test_cross_company_isolation(self):
        company_a = self.env["res.company"].create({"name": "Company A CRM"})
        company_b = self.env["res.company"].create({"name": "Company B CRM"})

        lead_a = self.env["crm.lead"].create(
            {"name": "Lead A", "type": "lead", "company_id": company_a.id}
        )
        request_a = self.env["amnus.crm.project.request"].create(
            {"lead_id": lead_a.id, "company_id": company_a.id}
        )

        user_b = self.env["res.users"].create(
            {
                "name": "User B CRM",
                "login": "user_b_crm",
                "company_ids": [(6, 0, [company_b.id])],
                "company_id": company_b.id,
                "group_ids": [(6, 0, [self.env.ref("amnus_core.group_amnus_user").id])],
            }
        )
        request_user_b = self.env["amnus.crm.project.request"].with_user(user_b)
        found = request_user_b.search([("id", "=", request_a.id)])
        self.assertEqual(len(found), 0, "Cross-company request access must be blocked")
