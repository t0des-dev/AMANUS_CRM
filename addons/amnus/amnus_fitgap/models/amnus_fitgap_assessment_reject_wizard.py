# -*- coding: utf-8 -*-
"""Wizard to collect a rejection reason for a Fit-Gap assessment."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AmnusFitgapAssessmentRejectWizard(models.TransientModel):
    _name = "amnus.fitgap.assessment.reject.wizard"
    _description = "Reject Fit-Gap Assessment Wizard"

    assessment_id = fields.Many2one(
        "amnus.fitgap.assessment",
        string="Assessment",
        required=True,
        ondelete="cascade",
    )
    rejection_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.assessment_id.action_reject(rejection_reason=self.rejection_reason)
        return {"type": "ir.actions.act_window_close"}
