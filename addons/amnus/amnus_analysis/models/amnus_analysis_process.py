# -*- coding: utf-8 -*-
"""AMNUS Analysis process: AS-IS / TO-BE business process documentation."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusAnalysisProcess(models.Model):
    """AMNUS Analysis process: AS-IS / TO-BE business process documentation.

    A process documents the customer's existing (AS-IS) and proposed
    (TO-BE) business processes for a business area. This model is intentionally
    simple: it does not require a visual process designer or BPMN editor.
    """

    _name = "amnus.analysis.process"
    _description = "AMNUS Analysis Process"
    _inherit = ["mail.thread"]
    _order = "project_id, reference, id"
    _rec_name = "reference"

    name = fields.Char(
        string="Process Name",
        required=True,
        tracking=True,
        help="Name of the business process.",
    )
    reference = fields.Char(
        string="Process Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        help="Stable process identifier (e.g. PRC-00001).",
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Implementation project this process belongs to.",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="project_id.partner_id",
        store=True,
        readonly=True,
    )
    category = fields.Selection(
        [
            ("business", "Business Process"),
            ("technical", "Technical Process"),
            ("data", "Data Process"),
            ("integration", "Integration Process"),
            ("other", "Other"),
        ],
        string="Process Category",
        default="business",
        tracking=True,
    )
    as_is_description = fields.Text(
        string="AS-IS Description",
        help="Description of the customer's existing process.",
    )
    to_be_description = fields.Text(
        string="TO-BE Description",
        help="Description of the proposed target process.",
    )
    requirement_ids = fields.Many2many(
        "amnus.analysis.requirement",
        string="Related Requirements",
        help="Requirements that relate to this process.",
    )
    owner_id = fields.Many2one(
        "res.users",
        string="Process Owner",
        default=lambda self: self.env.user,
        tracking=True,
    )
    notes = fields.Text(string="Internal Notes")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    @api.constrains("requirement_ids", "project_id")
    def _check_requirement_project(self):
        """Linked requirements must belong to the same project as the process."""
        for process in self:
            for requirement in process.requirement_ids:
                if requirement.project_id != process.project_id:
                    raise ValidationError(
                        _("All related requirements must belong to the same project as the process.")
                    )

    _process_reference_unique = models.Constraint(
        "unique (reference)",
        "Process reference must be unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create processes with a generated reference and draft state."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A process must be created in Draft state."))
            if vals.get("reference", _("New")) == _("New"):
                sequence = self.env["ir.sequence"].next_by_code("amnus.analysis.process")
                vals["reference"] = sequence or _("New")
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        """Protect lifecycle transitions."""
        if "state" in vals and not self.env.su:
            raise UserError(
                _("Process status cannot be changed directly. Use the workflow actions.")
            )
        return super().write(vals)

    def unlink(self):
        """Protect approved process records from deletion."""
        for process in self:
            if process.state == "approved":
                raise UserError(_("Approved processes cannot be deleted. Archive them instead."))
        return super().unlink()

    def action_submit_for_review(self):
        """Submit a draft process for review."""
        for process in self:
            if process.state != "draft":
                raise UserError(_("Only draft processes can be submitted for review."))
        self._internal_write({"state": "reviewed"})
        return True

    def action_approve(self):
        """Approve a reviewed process."""
        if not self.env.su and not self.env.user.has_group(
            "amnus_analysis.group_amnus_analysis_manager"
        ):
            raise UserError(_("Only an AMNUS Analysis Manager can approve processes."))
        for process in self:
            if process.state != "reviewed":
                raise UserError(_("Only reviewed processes can be approved."))
        self._internal_write({"state": "approved"})
        return True

    def action_cancel(self):
        """Cancel a draft or reviewed process."""
        for process in self:
            if process.state not in ("draft", "reviewed"):
                raise UserError(_("Only draft or reviewed processes can be cancelled."))
        self._internal_write({"state": "cancelled"})
        return True

    def _internal_write(self, vals):
        return models.Model.write(self.sudo(), vals)
