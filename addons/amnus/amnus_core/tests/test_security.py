# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import AccessError


@tagged("standard", "amnus_core", "at_install", "-post_install")
class TestAmnusSecurity(common.TransactionCase):
    """Tests for AMNUS security groups, access rights and menus."""

    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref("amnus_core.group_amnus_user")
        self.group_manager = self.env.ref("amnus_core.group_amnus_manager")
        self.group_admin = self.env.ref("amnus_core.group_amnus_admin")
        self.User = self.env["res.users"]

    def _make_user(self, name, login, groups):
        return self.User.create(
            {
                "name": name,
                "login": login,
                "group_ids": [(6, 0, groups)],
            }
        )

    # --- Groups ----------------------------------------------------------

    def test_groups_exist(self):
        self.assertTrue(self.group_user)
        self.assertTrue(self.group_manager)
        self.assertTrue(self.group_admin)

    def test_group_implication_hierarchy(self):
        self.assertIn(self.group_user, self.group_manager.implied_ids)
        self.assertIn(self.group_manager, self.group_admin.implied_ids)

    def test_create_users_with_groups(self):
        amnus_user = self._make_user("AMNUS User", "amnus_sec_user", [self.group_user.id])
        amnus_manager = self._make_user(
            "AMNUS Manager", "amnus_sec_manager", [self.group_manager.id]
        )
        self.assertIn(self.group_user, amnus_user.group_ids)
        # Manager implies User.
        self.assertIn(self.group_user, amnus_manager.all_group_ids)
        self.assertIn(self.group_manager, amnus_manager.group_ids)

    # --- Tag access rights ----------------------------------------------

    def test_tag_model_access_for_user(self):
        amnus_user = self._make_user("AMNUS Tag User", "amnus_tag_user", [self.group_user.id])
        tag_user = self.env["amnus.tag"].with_user(amnus_user)
        # User can read, create, write but not unlink tags.
        self.assertTrue(tag_user.has_access("read"))
        self.assertTrue(tag_user.has_access("create"))
        self.assertTrue(tag_user.has_access("write"))
        self.assertFalse(tag_user.has_access("unlink"))

    def test_tag_unlink_denied_for_user(self):
        amnus_user = self._make_user("AMNUS User", "amnus_unlink_user", [self.group_user.id])
        tag = self.env["amnus.tag"].create({"name": "Unlink Test", "category": "general"})
        with self.assertRaises(Exception):
            tag.with_user(amnus_user).unlink()

    def test_tag_unlink_allowed_for_manager(self):
        amnus_manager = self._make_user("AMNUS Manager", "amnus_unlink_mgr", [self.group_manager.id])
        tag = self.env["amnus.tag"].create({"name": "Manager Unlink Test", "category": "general"})
        # Manager should be able to unlink tags.
        tag.with_user(amnus_manager).unlink()
        self.assertFalse(self.env["amnus.tag"].search([("id", "=", tag.id)]))

    # --- Audit log access restrictions ----------------------------------

    def test_audit_log_access_restricted_for_user(self):
        amnus_user = self._make_user(
            "AMNUS Audit User", "amnus_sec_audit", [self.group_user.id]
        )
        audit_user = self.env["amnus.audit.log"].with_user(amnus_user)
        self.assertFalse(audit_user.has_access("create"))
        self.assertFalse(audit_user.has_access("read"))
        self.assertFalse(audit_user.has_access("write"))
        self.assertFalse(audit_user.has_access("unlink"))

    def test_manager_can_read_but_not_write_audit_log(self):
        amnus_manager = self._make_user(
            "AMNUS Manager", "amnus_sec_mgr", [self.group_manager.id]
        )
        audit_manager = self.env["amnus.audit.log"].with_user(amnus_manager)
        self.assertTrue(audit_manager.has_access("read"))
        self.assertFalse(audit_manager.has_access("create"))
        self.assertFalse(audit_manager.has_access("write"))
        self.assertFalse(audit_manager.has_access("unlink"))

    # --- Menus -----------------------------------------------------------

    def test_amnus_root_menu_exists(self):
        menu = self.env.ref("amnus_core.menu_amnus_root", raise_if_not_found=False)
        self.assertTrue(menu, "AMNUS root menu must exist")
        if menu:
            self.assertEqual(menu.name, "AMNUS")

    def test_menu_group_restrictions(self):
        menus = {
            "menu_amnus_tags": self.group_user,
            "menu_amnus_audit_logs": self.group_manager,
            "menu_amnus_settings": self.group_admin,
        }
        for xml_id, required_group in menus.items():
            menu = self.env.ref("amnus_core.%s" % xml_id, raise_if_not_found=False)
            self.assertTrue(menu, "Menu %s must exist" % xml_id)
            if menu:
                self.assertIn(required_group, menu.group_ids)

    # --- Cross-company access -------------------------------------------

    def test_cross_company_tag_access_blocked(self):
        company_a = self.env["res.company"].create({"name": "Company A"})
        company_b = self.env["res.company"].create({"name": "Company B"})

        tag_a = self.env["amnus.tag"].create(
            {"name": "Co A Tag", "category": "general", "company_id": company_a.id}
        )

        # A user belonging only to Company B must not see Company A's tag.
        user_b = self.env["res.users"].create(
            {
                "name": "User B",
                "login": "user_b_cross",
                "company_ids": [(6, 0, [company_b.id])],
                "company_id": company_b.id,
                "group_ids": [(6, 0, [self.group_user.id])],
            }
        )
        tag_user_b = self.env["amnus.tag"].with_user(user_b).with_context(
            allowed_company_ids=[company_b.id],
        )
        found = tag_user_b.search([("id", "=", tag_a.id)])
        self.assertEqual(len(found), 0, "Cross-company tag access must be blocked")

        # Global tag (no company) is visible to all companies.
        tag_global = self.env["amnus.tag"].create(
            {"name": "Global Tag", "category": "general", "company_id": False}
        )
        found_global = tag_user_b.search([("id", "=", tag_global.id)])
        self.assertEqual(len(found_global), 1, "Global tag must be visible across companies")
