# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusProjectsInstallation(common.TransactionCase):
    """Installation, registry, views and standard-project compatibility."""

    def test_module_installed(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "amnus_projects")], limit=1
        )
        self.assertTrue(module, "amnus_projects must be registered")
        self.assertEqual(module.state, "installed")

    def test_required_dependencies_installed(self):
        for name in ("amnus_core", "amnus_crm", "project", "mail"):
            module = self.env["ir.module.module"].search(
                [("name", "=", name)], limit=1
            )
            self.assertTrue(module, f"{name} must be registered")
            self.assertEqual(module.state, "installed", f"{name} must be installed")

    def test_models_registered(self):
        self.assertIn("amnus.project.deliverable", self.env.registry.models)
        for field in (
            "amnus_is_amnus_project",
            "amnus_request_id",
            "amnus_request_type",
            "amnus_actual_go_live",
            "amnus_deliverable_ids",
            "amnus_deliverable_count",
            "amnus_tag_ids",
        ):
            self.assertIn(field, self.env["project.project"]._fields)
        self.assertIn(
            "amnus_deliverable_id", self.env["project.task"]._fields
        )
        for field in ("project_id", "project_count"):
            self.assertIn(
                field, self.env["amnus.crm.project.request"]._fields
            )

    def test_views_and_menus_registered(self):
        for xml_id in (
            "amnus_projects.edit_project_amnus",
            "amnus_projects.view_project_project_filter_amnus",
            "amnus_projects.view_task_form2_amnus",
            "amnus_projects.view_task_search_form_amnus",
            "amnus_projects.view_amnus_project_deliverable_list",
            "amnus_projects.view_amnus_project_deliverable_form",
            "amnus_projects.view_amnus_project_deliverable_search",
            "amnus_projects.view_amnus_crm_project_request_form_amnus",
            "amnus_projects.view_amnus_crm_project_request_search_amnus",
            "amnus_projects.menu_amnus_projects_root",
            "amnus_projects.menu_amnus_projects",
            "amnus_projects.menu_amnus_deliverables",
            "amnus_projects.menu_amnus_projects_configuration",
            "amnus_projects.menu_amnus_project_stages",
            "amnus_projects.action_amnus_project_deliverables",
        ):
            self.assertTrue(
                self.env.ref(xml_id, raise_if_not_found=False),
                f"{xml_id} must exist",
            )

    def test_standard_project_compatibility(self):
        self.assertTrue(self.env["project.project"]._fields["stage_id"])
        self.assertTrue(self.env["project.project"]._fields["last_update_status"])
        self.assertTrue(self.env["project.project"]._fields["date_start"])
        self.assertTrue(self.env["project.project"]._fields["date"])
        self.assertTrue(self.env["project.task"]._fields["stage_id"])
        self.assertTrue(self.env["project.task"]._fields["state"])

    def test_standard_actions_and_stages_available(self):
        self.assertTrue(self.env.ref("project.open_view_project_all"))
        self.assertTrue(self.env.ref("project.project_project_stage_configure"))
        stage = self.env["project.project.stage"].create(
            {"name": "AMNUS Delivery Stage", "company_id": self.env.company.id}
        )
        self.assertTrue(stage.id)
        self.assertEqual(stage.company_id, self.env.company)
