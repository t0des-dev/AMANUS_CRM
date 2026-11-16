# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import AccessError


@tagged("standard", "amnus_core", "at_install", "-post_install")
class TestAmnusAuditLog(common.TransactionCase):
    """Tests for the AMNUS Audit Log shared model."""

    def setUp(self):
        super().setUp()
        self.audit_model = self.env["amnus.audit.log"]
        self.user_admin = self.env.ref("base.user_root")

    def test_audit_api_is_not_rpc_exposed(self):
        """_log_event is underscore-prefixed, so Odoo's execute_kw rejects it."""
        self.assertTrue(hasattr(self.audit_model, "_log_event"))
        self.assertTrue(self.audit_model._log_event.__name__.startswith("_"))

    def test_create_event_via_internal_api(self):
        audit = self.env["amnus.audit.log"]._log_event(
            name="Test Event",
            action="create",
            description="A test audit event",
            model_name="amnus.tag",
            record_id=1,
        )
        self.assertTrue(audit.id)
        self.assertEqual(audit.name, "Test Event")
        self.assertEqual(audit.action, "create")
        self.assertEqual(audit.description, "A test audit event")
        self.assertEqual(audit.model_name, "amnus.tag")
        self.assertEqual(audit.record_id, 1)
        self.assertIsNotNone(audit.date)
        # Identity derived from the authenticated environment (the superuser here).
        self.assertEqual(audit.user_id.id, self.env.user.id)
        self.assertEqual(audit.company_id.id, self.env.company.id)

    def test_audit_user_id_not_forgeable(self):
        """user_id is always derived from the environment, never from arguments."""
        vals = {
            "name": "Impersonated User",
            "login": "impersonated_user",
        }
        if "notification_type" in self.env["res.users"]._fields:
            vals["notification_type"] = "email"
        other_user = self.env["res.users"].create(vals)
        audit = self.env["amnus.audit.log"]._log_event(
            name="Identity Check",
            action="other",
        )
        # Even though no user_id was passed, it must be the current env user,
        # never an arbitrary value.
        self.assertEqual(audit.user_id.id, self.env.user.id)
        self.assertNotEqual(audit.user_id.id, other_user.id)

    def test_audit_company_from_environment(self):
        audit = self.env["amnus.audit.log"]._log_event(
            name="Company Check",
            action="other",
        )
        self.assertEqual(audit.company_id.id, self.env.company.id)

    def test_record_is_immutable(self):
        audit = self.env["amnus.audit.log"]._log_event(
            name="Immutable Event",
            action="other",
        )
        with self.assertRaises(AccessError):
            audit.write({"name": "Modified"})

    def test_record_cannot_be_deleted(self):
        audit = self.env["amnus.audit.log"]._log_event(
            name="To Delete",
            action="other",
        )
        with self.assertRaises(AccessError):
            audit.unlink()

    def test_ordinary_user_cannot_create_audit_record_directly(self):
        group_user = self.env.ref("amnus_core.group_amnus_user")
        vals = {
            "name": "AMNUS User",
            "login": "amnus_audit_user",
            "group_ids": [(6, 0, [group_user.id])],
        }
        if "notification_type" in self.env["res.users"]._fields:
            vals["notification_type"] = "email"
        amnus_user = self.env["res.users"].create(vals)
        audit_user = self.env["amnus.audit.log"].with_user(amnus_user)
        self.assertFalse(audit_user.has_access("create"))
        self.assertFalse(audit_user.has_access("write"))
        self.assertFalse(audit_user.has_access("unlink"))

    def test_ordinary_user_cannot_read_audit_log(self):
        group_user = self.env.ref("amnus_core.group_amnus_user")
        vals = {
            "name": "AMNUS User",
            "login": "amnus_audit_reader",
            "group_ids": [(6, 0, [group_user.id])],
        }
        if "notification_type" in self.env["res.users"]._fields:
            vals["notification_type"] = "email"
        amnus_user = self.env["res.users"].create(vals)
        audit_user = self.env["amnus.audit.log"].with_user(amnus_user)
        self.assertFalse(audit_user.has_access("read"))

    def test_manager_can_read_audit_log(self):
        group_manager = self.env.ref("amnus_core.group_amnus_manager")
        vals = {
            "name": "AMNUS Manager",
            "login": "amnus_mgr_reader",
            "group_ids": [(6, 0, [group_manager.id])],
        }
        if "notification_type" in self.env["res.users"]._fields:
            vals["notification_type"] = "email"
        manager = self.env["res.users"].create(vals)
        audit_manager = self.env["amnus.audit.log"].with_user(manager)
        self.assertTrue(audit_manager.has_access("read"))
        self.assertFalse(audit_manager.has_access("create"))
        self.assertFalse(audit_manager.has_access("write"))
