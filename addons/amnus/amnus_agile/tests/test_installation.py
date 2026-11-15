# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileInstallation(AmnusAgileTestMixin, common.TransactionCase):
    """Installation, registry, views and standard-project compatibility."""

    def test_module_installed(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "amnus_agile")], limit=1
        )
        self.assertTrue(module, "amnus_agile must be registered")
        self.assertEqual(module.state, "installed")

    def test_required_dependencies_installed(self):
        for name in ("amnus_core", "amnus_projects", "project", "mail"):
            module = self.env["ir.module.module"].search(
                [("name", "=", name)], limit=1
            )
            self.assertTrue(module, f"{name} must be registered")
            self.assertEqual(module.state, "installed", f"{name} must be installed")

    def test_models_registered(self):
        self.assertIn("amnus.agile.user.story", self.env.registry.models)
        self.assertIn("amnus.agile.epic", self.env.registry.models)
        self.assertIn("amnus.agile.sprint", self.env.registry.models)
        self.assertIn("amnus.agile.burndown", self.env.registry.models)
        self.assertIn("amnus.agile.sprint.membership", self.env.registry.models)
        self.assertIn("amnus.agile.carry.over.wizard", self.env.registry.models)

    def test_views_and_menus_registered(self):
        for xml_id in (
            "amnus_agile.view_amnus_agile_user_story_list",
            "amnus_agile.view_amnus_agile_user_story_form",
            "amnus_agile.view_amnus_agile_user_story_kanban",
            "amnus_agile.view_amnus_agile_user_story_search",
            "amnus_agile.action_amnus_agile_user_story",
            "amnus_agile.view_amnus_agile_epic_list",
            "amnus_agile.view_amnus_agile_epic_form",
            "amnus_agile.view_amnus_agile_epic_kanban",
            "amnus_agile.view_amnus_agile_epic_search",
            "amnus_agile.action_amnus_agile_epic",
            "amnus_agile.view_amnus_agile_sprint_list",
            "amnus_agile.view_amnus_agile_sprint_form",
            "amnus_agile.view_amnus_agile_sprint_kanban",
            "amnus_agile.view_amnus_agile_sprint_search",
            "amnus_agile.action_amnus_agile_sprint",
            "amnus_agile.view_amnus_agile_burndown_list",
            "amnus_agile.view_amnus_agile_burndown_graph",
            "amnus_agile.action_amnus_agile_burndown",
            "amnus_agile.view_amnus_agile_sprint_velocity_list",
            "amnus_agile.view_amnus_agile_sprint_velocity_graph",
            "amnus_agile.action_amnus_agile_sprint_velocity",
            "amnus_agile.view_amnus_agile_carry_over_wizard_form",
            "amnus_agile.action_amnus_agile_carry_over_wizard",
            "amnus_agile.menu_amnus_agile_root",
            "amnus_agile.menu_amnus_agile_reporting",
            "amnus_agile.menu_amnus_agile_burndown",
            "amnus_agile.menu_amnus_agile_velocity",
        ):
            self.assertTrue(
                self.env.ref(xml_id, raise_if_not_found=False),
                f"{xml_id} must exist",
            )

    def test_standard_project_compatibility(self):
        self.assertTrue(self.env["project.project"]._fields["stage_id"])
        self.assertTrue(self.env["project.task"]._fields["stage_id"])
        self.assertTrue(self.env["project.task"]._fields["state"])
