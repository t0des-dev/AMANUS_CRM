# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("standard", "amnus_core", "at_install", "-post_install")
class TestAmnusConfig(common.TransactionCase):
    """Tests for AMNUS configuration persistence."""

    def setUp(self):
        super().setUp()
        self.config_model = self.env["res.config.settings"]

    def test_settings_persist_and_read_back(self):
        settings = self.config_model.create(
            {
                "amnus_enabled": False,
                "amnus_audit_logging": True,
            }
        )
        settings.set_values()

        read_back = self.config_model.get_values()
        self.assertEqual(read_back["amnus_enabled"], False)
        self.assertEqual(read_back["amnus_audit_logging"], True)

    def test_defaults_when_no_configuration(self):
        read_back = self.config_model.get_values()
        # Defaults are True until explicitly changed.
        self.assertEqual(read_back["amnus_enabled"], True)
        self.assertEqual(read_back["amnus_audit_logging"], True)

    def test_toggle_persists(self):
        settings = self.config_model.create({"amnus_enabled": True})
        settings.set_values()
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("amnus_core.enabled"),
            "True",
        )
        settings.write({"amnus_enabled": False})
        settings.set_values()
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("amnus_core.enabled"),
            "False",
        )
