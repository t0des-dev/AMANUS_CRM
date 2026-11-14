# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import common, tagged

from .common import AmnusProjectTestMixin


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusCrmHandover(AmnusProjectTestMixin, common.TransactionCase):
    """CRM implementation request -> AMNUS project handover."""

    def test_approved_request_creates_one_project(self):
        partner = self.env["res.partner"].create(
            {"name": "Handover Customer", "company_id": self.company.id}
        )
        tag = self.env["amnus.tag"].create({"name": "Handover", "category": "project"})
        lead, request = self._create_approved_request(
            partner_id=partner.id, request_type="integration"
        )
        lead.write({"amnus_tag_ids": [(6, 0, [tag.id])]})

        action = request.with_user(self.project_manager).action_create_project()

        project = self.env["project.project"].browse(action["res_id"])
        self.assertTrue(project.exists())
        self.assertTrue(project.amnus_is_amnus_project)
        self.assertEqual(project.amnus_request_id, request)
        self.assertEqual(project.partner_id, partner)
        self.assertEqual(project.company_id, self.company)
        self.assertEqual(project.name, lead.name)
        self.assertEqual(project.date_start, fields_date("2026-01-05"))
        self.assertEqual(project.date, fields_date("2026-06-30"))
        self.assertIn(request.scope_summary, project.description)
        self.assertEqual(project.user_id, self.project_manager)
        self.assertEqual(project.amnus_tag_ids, tag)
        self.assertEqual(request.project_id, project)
        self.assertEqual(request.project_count, 1)

    def test_handover_writes_audit_event(self):
        lead, request = self._create_approved_request()
        action = request.with_user(self.project_manager).action_create_project()
        project = self.env["project.project"].browse(action["res_id"])
        audit = self.env["amnus.audit.log"].search(
            [
                ("model_name", "=", "project.project"),
                ("record_id", "=", project.id),
                ("action", "=", "create"),
            ]
        )
        self.assertEqual(len(audit), 1)
        self.assertIn(request.name, audit.description or "")
        self.assertEqual(audit.user_id, self.project_manager)

    def test_handover_posts_project_message(self):
        lead, request = self._create_approved_request()
        action = request.with_user(self.project_manager).action_create_project()
        project = self.env["project.project"].browse(action["res_id"])
        self.assertTrue(
            any(
                request.name in (message.body or "")
                for message in project.message_ids
            ),
            "The project chatter must record the handover",
        )

    def test_unapproved_request_is_rejected(self):
        lead, request = self._create_approved_request(state="reviewed")
        with self.assertRaises(UserError):
            request.with_user(self.project_manager).action_create_project()
        self.assertFalse(request.project_id)

    def test_unauthorized_user_is_rejected(self):
        lead, request = self._create_approved_request()
        with self.assertRaises(UserError):
            request.with_user(self.project_user).action_create_project()
        self.assertFalse(request.project_id)

    def test_repeated_handover_is_rejected(self):
        lead, request = self._create_approved_request()
        request.with_user(self.project_manager).action_create_project()
        with self.assertRaises(UserError):
            request.with_user(self.project_manager).action_create_project()
        projects = self.env["project.project"].search(
            [("amnus_request_id", "=", request.id)]
        )
        self.assertEqual(len(projects), 1)

    def test_company_mismatch_is_rejected(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})
        lead = self.env["crm.lead"].create(
            {
                "name": "Other Company Opportunity",
                "type": "opportunity",
                "company_id": other_company.id,
            }
        )
        request = self.env["amnus.crm.project.request"].create(
            {
                "lead_id": lead.id,
                "company_id": self.company.id,
                "state": "approved",
            }
        )
        with self.assertRaises(UserError):
            request.with_user(self.project_manager).action_create_project()
        self.assertFalse(request.project_id)

    def test_child_contact_company_is_accepted(self):
        parent = self.env["res.partner"].create(
            {
                "name": "Commercial Entity",
                "is_company": True,
                "company_id": self.company.id,
            }
        )
        child = self.env["res.partner"].create(
            {
                "name": "Child Contact",
                "parent_id": parent.id,
            }
        )
        lead, request = self._create_approved_request(partner_id=child.id)
        action = request.with_user(self.project_manager).action_create_project()
        project = self.env["project.project"].browse(action["res_id"])
        self.assertEqual(project.partner_id, child)

    def test_client_cannot_forge_project_link(self):
        lead, request = self._create_approved_request()
        project = self._create_project("Unrelated Project")
        with self.assertRaises(UserError):
            request.with_user(self.project_user).write({"project_id": project.id})
        self.assertFalse(request.project_id)

    def test_failed_audit_rolls_back_the_handover(self):
        lead, request = self._create_approved_request()
        audit_model = type(self.env["amnus.audit.log"])
        with self.assertRaises(UserError), self.env.cr.savepoint():
            with patch.object(
                audit_model, "_log_event", side_effect=UserError("audit failure")
            ):
                request.with_user(self.project_manager).action_create_project()
        self.env.invalidate_all()
        self.assertFalse(request.project_id)
        self.assertFalse(
            self.env["project.project"].search(
                [("amnus_request_id", "=", request.id)]
            )
        )


def fields_date(value):
    """Convert an ISO date string to a ``datetime.date`` for comparisons."""
    from odoo import fields

    return fields.Date.to_date(value)
