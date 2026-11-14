# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectProject(models.Model):
    """AMNUS extensions for standard Odoo projects.

    The standard project model remains the single source of truth for the
    project, its lifecycle stage, its health and its tasks. AMNUS only adds
    implementation metadata and the link to the originating CRM request.
    """

    _inherit = "project.project"

    amnus_is_amnus_project = fields.Boolean(
        string="AMNUS Project",
        default=False,
        index=True,
        copy=False,
        help="Whether this project is managed through the AMNUS lifecycle.",
    )
    amnus_request_id = fields.Many2one(
        "amnus.crm.project.request",
        string="Implementation Request",
        ondelete="set null",
        index=True,
        copy=False,
        readonly=True,
        help="Approved CRM implementation request this project originates from.",
    )
    amnus_request_type = fields.Selection(
        related="amnus_request_id.request_type",
        string="Request Type",
        store=True,
        readonly=True,
    )
    amnus_actual_go_live = fields.Date(
        string="Actual Go-Live",
        copy=False,
        tracking=True,
        help="Date on which the delivered solution actually went live.",
    )
    amnus_deliverable_ids = fields.One2many(
        "amnus.project.deliverable",
        "project_id",
        string="Deliverables",
    )
    amnus_deliverable_count = fields.Integer(
        string="Deliverables",
        compute="_compute_amnus_deliverable_count",
    )
    amnus_tag_ids = fields.Many2many(
        "amnus.tag",
        "amnus_project_project_tag_rel",
        "project_id",
        "tag_id",
        string="AMNUS Tags",
    )

    _amnus_request_unique = models.Constraint(
        "UNIQUE (amnus_request_id)",
        "Only one project can be linked to an implementation request.",
    )

    @api.depends("amnus_deliverable_ids")
    def _compute_amnus_deliverable_count(self):
        for project in self:
            project.amnus_deliverable_count = len(project.amnus_deliverable_ids)

    # ------------------------------------------------------------------
    # Integrity guards
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request_id = vals.get("amnus_request_id")
            if not request_id:
                continue
            request = self.env["amnus.crm.project.request"].browse(request_id)
            if request.state != "approved":
                raise ValidationError(
                    _("A project can only be created from an approved implementation request.")
                )
            if request.project_id:
                raise ValidationError(
                    _("This implementation request is already linked to a project.")
                )
            company_id = vals.get("company_id")
            if company_id and request.company_id and company_id != request.company_id.id:
                raise ValidationError(
                    _("The project company must match the implementation request company.")
                )
        projects = super().create(vals_list)
        # Keep the convenience backlink on the request in sync with the
        # authoritative project link, even when the project was created through
        # the ORM rather than the handover action.
        for project in projects:
            if (
                project.amnus_request_id
                and project.amnus_request_id.project_id != project
            ):
                project.amnus_request_id.sudo().write({"project_id": project.id})
        return projects

    def write(self, vals):
        # The request link is established once, by the handover method, and is
        # never editable afterwards. ``env.su`` is the trusted server-side
        # boundary: client RPC always runs with ``su = False``.
        if "amnus_request_id" in vals and not self.env.su:
            raise UserError(
                _("The implementation request link cannot be modified directly.")
            )
        return super().write(vals)

    def unlink(self):
        # Accepted deliverables are legal records: a project deletion must not
        # silently cascade-delete them. Archive the project instead.
        if not self.env.su and any(
            deliverable.state == "accepted"
            for project in self
            for deliverable in project.amnus_deliverable_ids
        ):
            raise UserError(
                _("This project contains accepted deliverables and cannot be deleted.")
            )
        return super().unlink()

    def action_view_amnus_request(self):
        """Open the implementation request that produced this project."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Implementation Request"),
            "res_model": "amnus.crm.project.request",
            "res_id": self.amnus_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_amnus_deliverables(self):
        """Open the deliverables of this project."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "amnus_projects.action_amnus_project_deliverables"
        )
        action["domain"] = [("project_id", "=", self.id)]
        action["context"] = {"default_project_id": self.id}
        return action
