# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("standard", "amnus_crm", "at_install", "-post_install")
class TestAmnusCrmInstallation(common.TransactionCase):
    """Tests for AMNUS CRM installation and integration."""

    def test_module_installed(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "amnus_crm")], limit=1
        )
        self.assertTrue(module, "amnus_crm module must be registered")
        self.assertEqual(module.state, "installed")

    def test_crm_lead_extension_loads(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Test Lead",
                "type": "lead",
            }
        )
        self.assertTrue(lead.id)
        self.assertFalse(lead.amnus_is_implementation)

    def test_amnus_crm_project_request_model_exists(self):
        request_model = self.env["amnus.crm.project.request"]
        self.assertEqual(request_model._name, "amnus.crm.project.request")
