# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.exceptions import AccessError


class TestAmnusAuditLog(common.TransactionCase):
    """Tests for the AMNUS Audit Log shared model."""

    def setUp(self):
        super().setUp()
        self.audit_model = self.env["amnus.audit.log"]
        self.user_admin = self.env.ref("base.user_root")

    def test_create_event_via_api(self):
        audit = self.env["amnus.audit.log"].with_user(self.user_admin).sudo().log_event(
            name="Test Event",
            action="create",
            description="A test audit event",
            model_name="amnus.tag",
            record_id=1,
        )
        self.assertTrue(audit.id)
        self.assertEqual(audit.name, "Test Event")
        self.assertEqual(audit.action, "create")
        self.assertIsNotNone(audit.date)
        self.assertEqual(audit.user_id, self.user_admin)

    def test_record_is_immutable(self):
        audit = self.env["amnus.audit.log"].with_user(self.user_admin).sudo().log_event(
            name="Immutable Event",
            action="other",
        )
        with self.assertRaises(AccessError):
            audit.write({"name": "Modified"})

    def test_record_cannot_be_deleted(self):
        audit = self.env["amnus.audit.log"].with_user(self.user_admin).sudo().log_event(
            name="To Delete",
            action="other",
        )
        with self.assertRaises(AccessError):
            audit.unlink()

    def test_ordinary_user_cannot_access_audit_log(self):
        group_user = self.env.ref("amnus_core.group_amnus_user")
        amnus_user = self.env["res.users"].create(
            {
                "name": "AMNUS User",
                "login": "amnus_audit_user",
                "groups_id": [(6, 0, [group_user.id])],
            }
        )
        audit_user = self.env["amnus.audit.log"].with_user(amnus_user)
        # No create permission on audit.log for AMNUS User
        self.assertFalse(audit_user.check_access_rights("create", raise_exception=False))
