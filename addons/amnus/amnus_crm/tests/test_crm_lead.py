# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError


@tagged("standard", "amnus_crm", "at_install", "-post_install")
class TestAmnusCrmLeadFields(common.TransactionCase):
    """Tests for AMNUS CRM lead fields."""

    def test_amnus_implementation_flag(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Impl Lead",
                "type": "lead",
                "amnus_is_implementation": True,
            }
        )
        self.assertTrue(lead.amnus_is_implementation)

    def test_request_type_selection(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Typed Lead",
                "type": "lead",
                "amnus_request_type": "migration",
            }
        )
        self.assertEqual(lead.amnus_request_type, "migration")

    def test_date_validation(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["crm.lead"].create(
                {
                    "name": "Date Lead",
                    "type": "lead",
                    "amnus_expected_start_date": "2026-01-01",
                    "amnus_expected_go_live": "2025-12-01",
                }
            )

    def test_estimated_users_validation(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Users Lead",
                "type": "lead",
                "amnus_estimated_users": 5,
            }
        )
        with self.assertRaises(ValidationError):
            lead.write({"amnus_estimated_users": -5})

    def test_amnus_tags_relation(self):
        tag = self.env["amnus.tag"].create({"name": "CRM Tag", "category": "project"})
        lead = self.env["crm.lead"].create(
            {
                "name": "Tagged Lead",
                "type": "lead",
                "amnus_tag_ids": [(6, 0, [tag.id])],
            }
        )
        self.assertEqual(len(lead.amnus_tag_ids), 1)
        self.assertEqual(lead.amnus_tag_ids[0].name, "CRM Tag")

    def test_normal_lead_creation(self):
        lead = self.env["crm.lead"].create(
            {
                "name": "Normal Lead",
                "type": "lead",
                "partner_name": "Test Company",
            }
        )
        self.assertTrue(lead.id)
        self.assertEqual(lead.name, "Normal Lead")
