# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from .common import AmnusProjectTestMixin


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusProjectSecurity(AmnusProjectTestMixin, common.TransactionCase):
    """Group hierarchy, ACLs, record rules and identity protection."""

    def test_group_hierarchy(self):
        self.assertTrue(
            self.project_user.has_group("project.group_project_user")
        )
        self.assertTrue(
            self.project_user.has_group("project.group_project_stages")
        )
        self.assertTrue(self.project_user.has_group("amnus_core.group_amnus_user"))
        self.assertTrue(
            self.project_manager.has_group("project.group_project_manager")
        )
        self.assertTrue(
            self.project_manager.has_group("amnus_projects.group_amnus_project_user")
        )
        self.assertTrue(
            self.project_admin.has_group(
                "amnus_projects.group_amnus_project_manager"
            )
        )

    def test_groups_are_not_auto_assigned(self):
        user = self.env["res.users"].create(
            {
                "name": "Plain Internal User",
                "login": "plain_internal_user_test",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        for group in (
            "amnus_projects.group_amnus_project_user",
            "amnus_projects.group_amnus_project_manager",
            "amnus_projects.group_amnus_project_admin",
        ):
            self.assertFalse(user.has_group(group))

    def test_project_user_has_read_only_project_access(self):
        project_model = self.env["project.project"].with_user(self.project_user)
        self.assertTrue(project_model.has_access("read"))
        self.assertFalse(project_model.has_access("create"))
        self.assertFalse(project_model.has_access("write"))
        self.assertFalse(project_model.has_access("unlink"))

    def test_project_manager_can_manage_projects(self):
        project_model = self.env["project.project"].with_user(self.project_manager)
        self.assertTrue(project_model.has_access("create"))
        self.assertTrue(project_model.has_access("write"))
        project = project_model.create({"name": "Manager Project"})
        project.write({"name": "Manager Project Updated"})
        self.assertEqual(project.name, "Manager Project Updated")

    def test_project_user_cannot_write_standard_project(self):
        project = self._create_project("Read-only Project")
        with self.assertRaises(AccessError):
            project.with_user(self.project_user).write({"name": "Hacked"})

    def test_deliverable_acl_per_group(self):
        deliverable_user = self.env["amnus.project.deliverable"].with_user(
            self.project_user
        )
        self.assertTrue(deliverable_user.has_access("read"))
        self.assertTrue(deliverable_user.has_access("create"))
        self.assertTrue(deliverable_user.has_access("write"))
        self.assertFalse(deliverable_user.has_access("unlink"))

        deliverable_manager = self.env["amnus.project.deliverable"].with_user(
            self.project_manager
        )
        self.assertTrue(deliverable_manager.has_access("unlink"))

        deliverable_admin = self.env["amnus.project.deliverable"].with_user(
            self.project_admin
        )
        self.assertTrue(deliverable_admin.has_access("unlink"))

    def test_cross_company_deliverable_is_hidden(self):
        company_a = self.env["res.company"].create({"name": "Deliverable Company A"})
        company_b = self.env["res.company"].create({"name": "Deliverable Company B"})
        project_a = self._create_project(
            "Company A Project", company_id=company_a.id
        )
        deliverable_a = self._create_deliverable(project_a, "Company A Deliverable")

        user_b = self.env["res.users"].create(
            {
                "name": "Company B Project User",
                "login": "company_b_project_user",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [
                    (6, 0, [self.project_user_group.id])
                ],
            }
        )
        found = self.env["amnus.project.deliverable"].with_user(user_b).search(
            [("id", "=", deliverable_a.id)]
        )
        self.assertFalse(found, "Cross-company deliverables must be hidden")
        with self.assertRaises(AccessError):
            deliverable_a.with_user(user_b).read(["name"])

    def test_multi_company_user_can_read_allowed_company(self):
        company_a = self.env["res.company"].create({"name": "Multi Company A"})
        company_b = self.env["res.company"].create({"name": "Multi Company B"})
        project_a = self._create_project(
            "Multi Company Project", company_id=company_a.id
        )
        deliverable_a = self._create_deliverable(project_a, "Multi Company Deliverable")
        user = self.env["res.users"].create(
            {
                "name": "Multi Company Project User",
                "login": "multi_company_project_user",
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id, company_b.id])],
                "group_ids": [(6, 0, [self.project_user_group.id])],
            }
        )
        self.assertEqual(
            self.env["amnus.project.deliverable"]
            .with_user(user)
            .search([("id", "=", deliverable_a.id)]),
            deliverable_a,
        )

    def test_user_cannot_create_deliverable_in_foreign_company(self):
        company_a = self.env["res.company"].create({"name": "Foreign Deliverable A"})
        company_b = self.env["res.company"].create({"name": "Foreign Deliverable B"})
        project_a = self._create_project(
            "Foreign Project", company_id=company_a.id
        )
        user_b = self.env["res.users"].create(
            {
                "name": "Foreign Company User",
                "login": "foreign_company_project_user",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.project_user_group.id])],
            }
        )
        with self.assertRaises(AccessError):
            self.env["amnus.project.deliverable"].with_user(user_b).create(
                {
                    "name": "Forged Company Deliverable",
                    "project_id": project_a.id,
                    "type": "document",
                }
            )

    def test_user_cannot_forge_sign_off(self):
        project = self._create_project("Sign-off Project")
        deliverable = self._create_deliverable(project, "Sign-off Deliverable")
        with self.assertRaises(UserError):
            deliverable.with_user(self.project_user).write(
                {"submitted_by": self.project_manager.id}
            )
        with self.assertRaises(UserError):
            self.env["amnus.project.deliverable"].with_user(
                self.project_user
            ).create(
                {
                    "name": "Forged",
                    "project_id": project.id,
                    "type": "document",
                    "accepted_by": self.project_manager.id,
                }
            )
