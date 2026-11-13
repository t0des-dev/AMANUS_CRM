# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError, UserError


@tagged("standard", "amnus_crm", "at_install", "-post_install")
class TestAmnusCrmProjectRequest(common.TransactionCase):
    """Tests for AMNUS CRM Project Request model."""

    def test_create_request(self):
        lead = self.env["crm.lead"].create({"name": "Req Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create(
            {
                "lead_id": lead.id,
                "description": "Test request",
            }
        )
        self.assertTrue(request.id)
        self.assertTrue(request.name.startswith("AMNUS-CRM-"))
        self.assertEqual(request.state, "draft")

    def test_required_lead(self):
        # lead_id is required; creating without it must fail.
        self.assertTrue(
            self.env["amnus.crm.project.request"]._fields["lead_id"].required
        )

    def test_sequence_generation(self):
        lead = self.env["crm.lead"].create({"name": "Seq Lead", "type": "lead"})
        req1 = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        req2 = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        self.assertNotEqual(req1.name, req2.name)

    def test_request_lead_relationship(self):
        lead = self.env["crm.lead"].create({"name": "Rel Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        self.assertEqual(request.lead_id, lead)
        self.assertEqual(request.partner_id, lead.partner_id)

    def test_state_transitions(self):
        lead = self.env["crm.lead"].create({"name": "State Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        self.assertEqual(request.state, "draft")

        request.action_submit()
        self.assertEqual(request.state, "submitted")

        request.action_review()
        self.assertEqual(request.state, "reviewed")

        request.action_approve()
        self.assertEqual(request.state, "approved")

    def test_invalid_transitions(self):
        lead = self.env["crm.lead"].create({"name": "Invalid Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})

        with self.assertRaises(UserError):
            request.action_approve()  # Can't approve from draft

        request.action_submit()
        request.action_approve()
        with self.assertRaises(UserError):
            request.action_cancel()  # Can't cancel approved

    def test_date_validation(self):
        lead = self.env["crm.lead"].create({"name": "Date Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create(
            {
                "lead_id": lead.id,
                "expected_start_date": "2026-01-01",
                "expected_go_live": "2026-02-01",
            }
        )
        with self.assertRaises(ValidationError):
            request.write(
                {
                    "expected_start_date": "2026-02-01",
                    "expected_go_live": "2026-01-01",
                }
            )

    def test_estimated_users_validation(self):
        lead = self.env["crm.lead"].create({"name": "Users Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create(
            {
                "lead_id": lead.id,
                "estimated_users": 5,
            }
        )
        with self.assertRaises(ValidationError):
            request.write({"estimated_users": -3})

    def test_company_assignment(self):
        lead = self.env["crm.lead"].create({"name": "Company Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        self.assertEqual(request.company_id, self.env.company)

    def test_audit_on_submit(self):
        lead = self.env["crm.lead"].create({"name": "Audit Lead", "type": "lead"})
        request = self.env["amnus.crm.project.request"].create({"lead_id": lead.id})
        request.action_submit()
        audit = self.env["amnus.audit.log"].search(
            [("model_name", "=", "amnus.crm.project.request")], limit=1
        )
        self.assertTrue(audit, "Audit log entry should be created on submit")
