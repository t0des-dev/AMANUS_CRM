# -*- coding: utf-8 -*-
"""AMNUS Analysis workshop: a structured discovery session."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusAnalysisWorkshop(models.Model):
    """AMNUS Analysis workshop: a structured discovery session.

    Workshops are where requirements are elicited, discussed and validated with
    customers and internal stakeholders. A workshop can surface multiple
    requirements, and a requirement can reference the workshops that informed
    it.
    """

    _name = "amnus.analysis.workshop"
    _description = "AMNUS Analysis Workshop"
    _inherit = ["mail.thread"]
    _order = "date_start desc, id"
    _rec_name = "reference"

    name = fields.Char(
        string="Workshop Title",
        required=True,
        tracking=True,
        help="Short title of the workshop.",
    )
    reference = fields.Char(
        string="Workshop Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        help="Stable workshop identifier (e.g. WKS-00001).",
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Implementation project this workshop belongs to.",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="project_id.partner_id",
        store=True,
        readonly=True,
    )
    workshop_type = fields.Selection(
        [
            ("discovery", "Discovery"),
            ("interview", "Interview"),
            ("review", "Review"),
            ("demo", "Demonstration"),
            ("other", "Other"),
        ],
        string="Workshop Type",
        default="discovery",
        tracking=True,
    )
    date_start = fields.Datetime(string="Start Date/Time", required=True, tracking=True)
    duration_hours = fields.Float(
        string="Duration (Hours)",
        default=1.0,
        tracking=True,
        help="Duration of the workshop in hours.",
    )
    location = fields.Char(
        string="Location / Meeting Link",
        help="Physical location or online meeting link.",
    )
    facilitator_id = fields.Many2one(
        "res.users",
        string="Facilitator",
        default=lambda self: self.env.user,
        tracking=True,
    )
    internal_participant_ids = fields.Many2many(
        "res.users",
        string="Internal Participants",
        help="AMNUS team members attending the workshop.",
    )
    customer_participant_ids = fields.Many2many(
        "res.partner",
        string="Customer Participants",
        help="Customer stakeholders attending the workshop.",
    )
    agenda = fields.Text(string="Agenda")
    discussion_notes = fields.Text(string="Discussion Notes")
    decisions = fields.Text(string="Decisions")
    outcomes = fields.Text(string="Outcomes")
    follow_up_actions = fields.Text(string="Follow-up Actions")
    requirement_ids = fields.Many2many(
        "amnus.analysis.requirement",
        string="Related Requirements",
        help="Requirements identified or refined during this workshop.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("held", "Held"),
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
        """Linked requirements must belong to the same project as the workshop."""
        for workshop in self:
            for requirement in workshop.requirement_ids:
                if requirement.project_id != workshop.project_id:
                    raise ValidationError(
                        _("All related requirements must belong to the same project as the workshop.")
                    )

    _workshop_reference_unique = models.Constraint(
        "unique (reference)",
        "Workshop reference must be unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create workshops with a generated reference and draft state."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A workshop must be created in Draft state."))
            if vals.get("reference", _("New")) == _("New"):
                sequence = self.env["ir.sequence"].next_by_code("amnus.analysis.workshop")
                vals["reference"] = sequence or _("New")
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        """Protect lifecycle transitions."""
        if "state" in vals and not self.env.su:
            raise UserError(
                _("Workshop status cannot be changed directly. Use the workflow actions.")
            )
        return super().write(vals)

    def unlink(self):
        """Protect held workshops from deletion."""
        for workshop in self:
            if workshop.state == "held":
                raise UserError(_("Held workshops cannot be deleted. Archive them instead."))
        return super().unlink()

    def action_mark_held(self):
        """Mark the workshop as held."""
        for workshop in self:
            if workshop.state != "draft":
                raise UserError(_("Only draft workshops can be marked as held."))
        self._internal_write({"state": "held"})
        return True

    def action_cancel(self):
        """Cancel a draft workshop."""
        for workshop in self:
            if workshop.state != "draft":
                raise UserError(_("Only draft workshops can be cancelled."))
        self._internal_write({"state": "cancelled"})
        return True

    def _internal_write(self, vals):
        return models.Model.write(self.sudo(), vals)
