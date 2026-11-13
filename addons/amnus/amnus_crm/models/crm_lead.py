# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    amnus_is_implementation = fields.Boolean(
        string="AMNUS Implementation",
        default=False,
        help="Whether this opportunity concerns an Odoo implementation or development project.",
    )
    amnus_request_type = fields.Selection(
        [
            ("new_implementation", "New Implementation"),
            ("customization", "Customization"),
            ("migration", "Migration"),
            ("integration", "Integration"),
            ("support", "Support"),
            ("training", "Training"),
            ("consulting", "Consulting"),
            ("other", "Other"),
        ],
        string="Request Type",
        default="new_implementation",
    )
    amnus_project_summary = fields.Text(
        string="Project Summary",
        help="Description of the requested Odoo solution.",
    )
    amnus_current_system = fields.Char(
        string="Current System",
        help="The customer's current system or ERP.",
    )
    amnus_expected_start_date = fields.Date(
        string="Expected Start Date",
    )
    amnus_expected_go_live = fields.Date(
        string="Expected Go-Live",
    )
    amnus_estimated_users = fields.Integer(
        string="Estimated Users",
        default=0,
    )
    amnus_company_size = fields.Selection(
        [
            ("small", "1-10 employees"),
            ("medium", "11-50 employees"),
            ("large", "51-250 employees"),
            ("enterprise", "250+ employees"),
        ],
        string="Company Size",
    )
    amnus_technical_notes = fields.Text(
        string="Technical Notes",
        help="Internal technical notes for the implementation team.",
    )
    amnus_tag_ids = fields.Many2many(
        "amnus.tag",
        "amnus_crm_lead_tag_rel",
        "lead_id",
        "tag_id",
        string="AMNUS Tags",
    )

    @api.constrains("amnus_expected_start_date", "amnus_expected_go_live")
    def _check_amnus_dates(self):
        for record in self:
            if (
                record.amnus_expected_start_date
                and record.amnus_expected_go_live
                and record.amnus_expected_go_live < record.amnus_expected_start_date
            ):
                raise ValidationError(
                    _("Expected go-live date must not precede the expected start date.")
                )

    @api.constrains("amnus_estimated_users")
    def _check_amnus_estimated_users(self):
        for record in self:
            if record.amnus_estimated_users is not None and record.amnus_estimated_users < 0:
                raise ValidationError(_("Estimated users must not be negative."))
