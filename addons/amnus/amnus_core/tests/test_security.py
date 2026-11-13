# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.exceptions import AccessError


class TestAmnusSecurity(common.TransactionCase):
    """Tests for AMNUS security groups and access rights."""

    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref("amnus_core.group_amnus_user")
        self.group_manager = self.env.ref("amnus_core.group_amnus_manager")
        self.group_admin = self.env.ref("amnus_core.group_amnus_admin")
        self.User = self.env["res.users"]

    def test_groups_exist(self):
        self.assertTrue(self.group_user)
        self.assertTrue(self.group_manager)
        self.assertTrue(self.group_admin)

    def test_group_implication_hierarchy(self):
        self.assertIn(self.group_user, self.group_manager.implied_ids)
        self.assertIn(self.group_manager, self.group_admin.implied_ids)

    def test_create_users_with_groups(self):
        amnus_user = self.User.create(
            {
                "name": "AMNUS User",
                "login": "amnus_sec_user",
                "groups_id": [(6, 0, [self.group_user.id])],
            }
        )
        amnus_manager = self.User.create(
            {
                "name": "AMNUS Manager",
                "login": "amnus_sec_manager",
                "groups_id": [(6, 0, [self.group_manager.id])],
            }
        )
        self.assertIn(self.group_user, amnus_user.groups_id)
        self.assertIn(self.group_user, amnus_manager.groups_id)  # implied
        self.assertIn(self.group_manager, amnus_manager.groups_id)

    def test_tag_model_access_for_user(self):
        amnus_user = self.User.create(
            {
                "name": "AMNUS User",
                "login": "amnus_tag_user",
                "groups_id": [(6, 0, [self.group_user.id])],
            }
        )
        tag_user = self.env["amnus.tag"].with_user(amnus_user)
        self.assertTrue(tag_user.check_access_rights("read", raise_exception=False))
        self.assertTrue(tag_user.check_access_rights("create", raise_exception=False))
        self.assertTrue(tag_user.check_access_rights("write", raise_exception=False))
        self.assertFalse(tag_user.check_access_rights("unlink", raise_exception=False))

    def test_audit_log_access_restricted(self):
        amnus_user = self.User.create(
            {
                "name": "AMNUS User",
                "login": "amnus_audit_user2",
                "groups_id": [(6, 0, [self.group_user.id])],
            }
        )
        audit_user = self.env["amnus.audit.log"].with_user(amnus_user)
        self.assertFalse(audit_user.check_access_rights("create", raise_exception=False))
        self.assertFalse(audit_user.check_access_rights("write", raise_exception=False))
        self.assertFalse(audit_user.check_access_rights("unlink", raise_exception=False))
