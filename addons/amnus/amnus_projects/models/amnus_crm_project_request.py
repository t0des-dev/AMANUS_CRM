# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusCrmProjectRequest(models.Model):
    """AMNUS handover from an approved CRM request to a real project."""

    _inherit = "amnus.crm.project.request"

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        readonly=True,
        copy=False,
        ondelete="set null",
        index=True,
        help="Project created from this implementation request.",
    )
    project_count = fields.Integer(
        string="Projects",
        compute="_compute_project_count",
    )

    @api.depends("project_id")
    def _compute_project_count(self):
        for request in self:
            request.project_count = 1 if request.project_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("project_id"):
                raise UserError(
                    _("A project can only be linked through the handover action.")
                )
        return super().create(vals_list)

    def write(self, vals):
        # The project link is written exclusively by ``action_create_project``
        # through a superuser write. Direct RPC writes must never be able to
        # forge the request/project relationship.
        if "project_id" in vals and not self.env.su:
            raise UserError(
                _("The project link can only be set through the handover action.")
            )
        return super().write(vals)

    @api.constrains("project_id")
    def _check_amnus_project_link(self):
        for request in self:
            if request.project_id and request.project_id.amnus_request_id != request:
                raise ValidationError(
                    _("The linked project is not attached to this implementation request.")
                )

    def _check_amnus_company_consistency(self):
        """Validate request, opportunity, customer and project company scopes.

        A customer contact may be a child contact of a commercial entity: when
        the contact itself has no company, its commercial entity company is
        used instead of rejecting a legitimate child contact.
        """
        self.ensure_one()
        company = self.company_id
        if not company:
            raise UserError(_("The implementation request has no company."))
        if company not in self.env.companies:
            raise UserError(
                _("You are not allowed to create a project for this company.")
            )
        if self.lead_id.company_id and self.lead_id.company_id != company:
            raise UserError(
                _("The opportunity company does not match the request company.")
            )
        partner = self.partner_id
        if partner:
            partner_company = partner.company_id or partner.commercial_partner_id.company_id
            if partner_company and partner_company != company:
                raise UserError(
                    _("The customer company does not match the request company.")
                )

    def action_create_project(self):
        """Create one project from this approved implementation request.

        The request row is locked for the duration of the transaction, then the
        approval state and existing project link are re-checked. A database
        unique constraint on ``project.project.amnus_request_id`` provides a
        second safety net against concurrent handovers.
        """
        self.ensure_one()
        if not (
            self.env.su
            or self.env.user.has_group("amnus_projects.group_amnus_project_manager")
        ):
            raise UserError(
                _("Only an AMNUS Project Manager can create a project from a request.")
            )
        self._check_amnus_company_consistency()

        # Serialize concurrent handovers on the request row.
        self.env.cr.execute(
            "SELECT state, project_id FROM amnus_crm_project_request WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        row = self.env.cr.fetchone()
        if not row:
            raise UserError(_("The implementation request no longer exists."))
        state, linked_project_id = row
        if state != "approved":
            raise UserError(
                _("Only approved implementation requests can be converted into a project.")
            )
        if linked_project_id:
            raise UserError(
                _("This implementation request is already linked to a project.")
            )

        lead = self.lead_id
        project = self.env["project.project"].create(
            {
                "name": lead.name or self.name,
                "partner_id": self.partner_id.id or False,
                "user_id": (self.user_id or lead.user_id or self.env.user).id,
                "company_id": self.company_id.id,
                "date_start": self.expected_start_date,
                "date": self.expected_go_live,
                "description": self.scope_summary or self.description or False,
                "amnus_is_amnus_project": True,
                "amnus_request_id": self.id,
                "amnus_tag_ids": [(6, 0, lead.amnus_tag_ids.ids)],
            }
        )
        self.sudo().write({"project_id": project.id})
        self.env["amnus.audit.log"]._log_event(
            name=_("Project Created from Implementation Request"),
            action="create",
            description=_(
                "Project %(project)s created from implementation request %(request)s.",
                project=project.name,
                request=self.name,
            ),
            model_name="project.project",
            record_id=project.id,
        )
        project.message_post(
            body=_(
                "Created from implementation request %(request)s for customer %(customer)s.",
                request=self.name,
                customer=self.partner_id.display_name or _("Unknown customer"),
            )
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Project"),
            "res_model": "project.project",
            "res_id": project.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_project(self):
        """Open the project created from this request."""
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("No project is linked to this implementation request."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Project"),
            "res_model": "project.project",
            "res_id": self.project_id.id,
            "view_mode": "form",
            "target": "current",
        }
