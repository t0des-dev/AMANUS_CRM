# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AmnusCrmProjectRequest(models.Model):
    _name = "amnus.crm.project.request"
    _description = "AMNUS CRM Project Implementation Request"
    _order = "create_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        default=lambda self: _("New"),
        copy=False,
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Opportunity",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="lead_id.partner_id",
        store=True,
        readonly=True,
    )
    contact_id = fields.Many2one(
        "res.partner",
        string="Contact",
        related="lead_id.partner_id",
        store=True,
        readonly=True,
    )
    request_type = fields.Selection(
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
        required=True,
    )
    description = fields.Text(string="Description")
    scope_summary = fields.Text(string="Scope Summary")
    expected_start_date = fields.Date(string="Expected Start Date")
    expected_go_live = fields.Date(string="Expected Go-Live")
    estimated_users = fields.Integer(string="Estimated Users", default=0)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )
    notes = fields.Text(string="Internal Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "amnus.crm.project.request"
                ) or _("New")
        return super().create(vals_list)

    @api.constrains("expected_start_date", "expected_go_live")
    def _check_dates(self):
        for record in self:
            if (
                record.expected_start_date
                and record.expected_go_live
                and record.expected_go_live < record.expected_start_date
            ):
                raise ValidationError(
                    _("Expected go-live date must not precede the expected start date.")
                )

    @api.constrains("estimated_users")
    def _check_estimated_users(self):
        for record in self:
            if record.estimated_users is not None and record.estimated_users < 0:
                raise ValidationError(_("Estimated users must not be negative."))

    # ---- Workflow transitions ----

    def action_submit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be submitted."))
            record.state = "submitted"
            self.env["amnus.audit.log"]._log_event(
                name=_("CRM Request Submitted"),
                action="state_change",
                description=_("Request %s submitted.") % record.name,
                model_name="amnus.crm.project.request",
                record_id=record.id,
            )

    def action_review(self):
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Only submitted requests can be reviewed."))
            record.state = "reviewed"

    def action_approve(self):
        for record in self:
            if not (self.env.su or self.env.user.has_group("amnus_core.group_amnus_manager")):
                raise UserError(_("You do not have permission to approve requests."))
            if record.state not in ("submitted", "reviewed"):
                raise UserError(_("Only submitted or reviewed requests can be approved."))
            record.state = "approved"
            self.env["amnus.audit.log"]._log_event(
                name=_("CRM Request Approved"),
                action="state_change",
                description=_("Request %s approved.") % record.name,
                model_name="amnus.crm.project.request",
                record_id=record.id,
            )

    def action_reject(self):
        for record in self:
            if not (self.env.su or self.env.user.has_group("amnus_core.group_amnus_manager")):
                raise UserError(_("You do not have permission to reject requests."))
            if record.state not in ("submitted", "reviewed"):
                raise UserError(_("Only submitted or reviewed requests can be rejected."))
            record.state = "rejected"

    def action_cancel(self):
        for record in self:
            if record.state in ("approved", "rejected", "cancelled"):
                raise UserError(_("This request cannot be cancelled."))
            record.state = "cancelled"
