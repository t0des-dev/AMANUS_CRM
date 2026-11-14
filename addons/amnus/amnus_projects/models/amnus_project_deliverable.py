# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AmnusProjectDeliverable(models.Model):
    """Contractual output of an AMNUS implementation project.

    A deliverable is not a project milestone: a milestone is a dated progress
    marker, while a deliverable carries a type, an acceptance workflow and a
    server-recorded sign-off. The standard ``project.milestone`` model is left
    untouched and can be linked in a later sprint.
    """

    _name = "amnus.project.deliverable"
    _description = "AMNUS Project Deliverable"
    _inherit = ["mail.thread"]
    _order = "project_id, sequence, id"
    _rec_name = "name"

    # Fields that may only be written by the workflow methods.
    SIGN_OFF_FIELDS = {
        "submitted_by",
        "submitted_date",
        "accepted_by",
        "accepted_date",
        "rejected_by",
        "rejected_date",
    }
    # Business fields frozen for non-managers once the deliverable is accepted.
    LOCKED_AFTER_ACCEPT = {
        "name",
        "project_id",
        "type",
        "description",
        "responsible_id",
        "due_date",
        "tag_ids",
        "active",
    }

    name = fields.Char(string="Name", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    sequence = fields.Integer(string="Sequence", default=10)
    type = fields.Selection(
        [
            ("document", "Document"),
            ("software", "Software"),
            ("migration", "Data Migration"),
            ("integration", "Integration"),
            ("training", "Training"),
            ("other", "Other"),
        ],
        string="Type",
        required=True,
        default="other",
        tracking=True,
    )
    description = fields.Text(string="Description")
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )
    due_date = fields.Date(string="Due Date", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    submitted_by = fields.Many2one("res.users", string="Submitted By", readonly=True, copy=False)
    submitted_date = fields.Datetime(string="Submitted On", readonly=True, copy=False)
    accepted_by = fields.Many2one("res.users", string="Accepted By", readonly=True, copy=False)
    accepted_date = fields.Datetime(string="Accepted On", readonly=True, copy=False)
    rejected_by = fields.Many2one("res.users", string="Rejected By", readonly=True, copy=False)
    rejected_date = fields.Datetime(string="Rejected On", readonly=True, copy=False)
    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    tag_ids = fields.Many2many(
        "amnus.tag",
        "amnus_project_deliverable_tag_rel",
        "deliverable_id",
        "tag_id",
        string="AMNUS Tags",
    )
    task_ids = fields.One2many(
        "project.task",
        "amnus_deliverable_id",
        string="Tasks",
    )
    task_count = fields.Integer(string="Tasks", compute="_compute_task_count")
    active = fields.Boolean(string="Active", default=True)

    @api.depends("task_ids")
    def _compute_task_count(self):
        for deliverable in self:
            deliverable.task_count = len(deliverable.task_ids)

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _is_project_manager(self):
        """Return whether the current user may manage AMNUS deliverables."""
        return self.env.su or self.env.user.has_group(
            "amnus_projects.group_amnus_project_manager"
        )

    def _check_is_project_manager(self):
        if not self._is_project_manager():
            raise UserError(
                _("Only an AMNUS Project Manager can perform this action.")
            )

    # ------------------------------------------------------------------
    # ORM guards: transitions and sign-off must go through the workflow
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state", "draft") != "draft":
                raise UserError(
                    _("A deliverable must be created in Draft state.")
                )
            if set(vals) & self.SIGN_OFF_FIELDS:
                raise UserError(
                    _("Sign-off information cannot be set when creating a deliverable.")
                )
        return super().create(vals_list)

    def write(self, vals):
        # State and sign-off fields are only writable in a superuser context,
        # i.e. from the server-side workflow methods below (which use sudo()
        # after performing their own authorization checks). Context flags are
        # client-controllable through RPC, so they are deliberately not used
        # as a security boundary.
        if not self.env.su:
            if "state" in vals:
                raise UserError(
                    _("The deliverable status can only be changed through the workflow buttons.")
                )
            if set(vals) & self.SIGN_OFF_FIELDS:
                raise UserError(
                    _("Sign-off information cannot be modified directly.")
                )
        if "project_id" in vals:
            for deliverable in self:
                if deliverable.state != "draft":
                    raise UserError(
                        _("The project cannot be changed after the deliverable is submitted.")
                    )
                if deliverable.task_ids:
                    raise UserError(
                        _("The project cannot be changed while tasks are linked to the deliverable.")
                    )
        for deliverable in self:
            if (
                deliverable.state == "accepted"
                and (set(vals) & self.LOCKED_AFTER_ACCEPT)
                and not deliverable._is_project_manager()
            ):
                raise UserError(
                    _("An accepted deliverable can only be modified by an AMNUS Project Manager.")
                )
        return super().write(vals)

    def unlink(self):
        if not self.env.su and any(
            deliverable.state == "accepted" for deliverable in self
        ):
            raise UserError(
                _("Accepted deliverables cannot be deleted. Archive them instead.")
            )
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _check_can_submit(self):
        manager = self._is_project_manager()
        for deliverable in self:
            if deliverable.state not in ("draft", "rejected"):
                raise UserError(
                    _("Only draft or rejected deliverables can be submitted.")
                )
            if not manager and deliverable.responsible_id != self.env.user:
                raise UserError(
                    _("Only the responsible user or an AMNUS Project Manager can submit this deliverable.")
                )

    def action_submit(self):
        """Submit a draft or rejected deliverable for acceptance."""
        self._check_can_submit()
        values = {
            "state": "submitted",
            "submitted_by": self.env.user.id,
            "submitted_date": fields.Datetime.now(),
            "accepted_by": False,
            "accepted_date": False,
            "rejected_by": False,
            "rejected_date": False,
            "rejection_reason": False,
        }
        self.sudo().write(values)
        for deliverable in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Deliverable Submitted"),
                action="state_change",
                description=_("Deliverable %(name)s submitted.", name=deliverable.name),
                model_name=deliverable._name,
                record_id=deliverable.id,
            )
        return True

    def action_accept(self):
        """Accept a submitted deliverable and record the sign-off identity."""
        self._check_is_project_manager()
        for deliverable in self:
            if deliverable.state != "submitted":
                raise UserError(
                    _("Only submitted deliverables can be accepted.")
                )
        values = {
            "state": "accepted",
            "accepted_by": self.env.user.id,
            "accepted_date": fields.Datetime.now(),
            "rejected_by": False,
            "rejected_date": False,
            "rejection_reason": False,
        }
        self.sudo().write(values)
        for deliverable in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Deliverable Accepted"),
                action="state_change",
                description=_("Deliverable %(name)s accepted.", name=deliverable.name),
                model_name=deliverable._name,
                record_id=deliverable.id,
            )
        return True

    def action_reject(self):
        """Reject a submitted deliverable; a written reason is mandatory."""
        self._check_is_project_manager()
        for deliverable in self:
            if deliverable.state != "submitted":
                raise UserError(
                    _("Only submitted deliverables can be rejected.")
                )
            if not deliverable.rejection_reason or not deliverable.rejection_reason.strip():
                raise UserError(
                    _("A rejection reason is required to reject a deliverable.")
                )
        values = {
            "state": "rejected",
            "rejected_by": self.env.user.id,
            "rejected_date": fields.Datetime.now(),
        }
        self.sudo().write(values)
        for deliverable in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Deliverable Rejected"),
                action="state_change",
                description=_("Deliverable %(name)s rejected.", name=deliverable.name),
                model_name=deliverable._name,
                record_id=deliverable.id,
            )
        return True

    def action_reset_to_draft(self):
        """Return a submitted or rejected deliverable to draft.

        Accepted deliverables are intentionally immutable, so no reset is
        allowed from the accepted state.
        """
        self._check_is_project_manager()
        for deliverable in self:
            if deliverable.state not in ("submitted", "rejected"):
                raise UserError(
                    _("Only submitted or rejected deliverables can be reset to draft.")
                )
        values = {
            "state": "draft",
            "submitted_by": False,
            "submitted_date": False,
            "accepted_by": False,
            "accepted_date": False,
            "rejected_by": False,
            "rejected_date": False,
            "rejection_reason": False,
        }
        self.sudo().write(values)
        for deliverable in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Deliverable Reset to Draft"),
                action="state_change",
                description=_("Deliverable %(name)s reset to draft.", name=deliverable.name),
                model_name=deliverable._name,
                record_id=deliverable.id,
            )
        return True

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_tasks(self):
        """Open the tasks linked to this deliverable."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tasks"),
            "res_model": "project.task",
            "view_mode": "list,form",
            "domain": [("amnus_deliverable_id", "=", self.id)],
            "context": {
                "default_amnus_deliverable_id": self.id,
                "default_project_id": self.project_id.id,
            },
        }
