# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("standard", "amnus_fitgap", "at_install", "-post_install")
class TestAmnusFitgapInstallation(common.TransactionCase):
    """Basic installation and model availability tests."""

    def test_models_available(self):
        self.assertTrue(self.env["amnus.fitgap.assessment"]._name)
        self.assertTrue(self.env["amnus.fitgap.assessment.version"]._name)

    def test_sequence_exists(self):
        sequence = self.env["ir.sequence"].search(
            [("code", "=", "amnus.fitgap.assessment")], limit=1
        )
        self.assertTrue(sequence)
        self.assertEqual(sequence.prefix, "FG-")
        self.assertEqual(sequence.padding, 5)

    def test_groups_exist(self):
        for xml_id in (
            "amnus_fitgap.group_amnus_fitgap_user",
            "amnus_fitgap.group_amnus_fitgap_manager",
            "amnus_fitgap.group_amnus_fitgap_admin",
        ):
            self.assertTrue(self.env.ref(xml_id))
