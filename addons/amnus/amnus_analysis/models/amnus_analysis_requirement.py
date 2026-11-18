# -*- coding: utf-8 -*-
"""AMNUS Analysis requirement: a customer business or functional requirement."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusAnalysisRequirement(models.Model):
    """AMNUS Analysis requirement: a customer business or functional requirement.

    A requirement is linked to one implementation project and carries a full
    lifecycle (draft, under review, approved, rejected, cancelled). Approved
    requirements are protected from silent rewrites and can only be changed
    through a controlled revision (return-to-review) workflow.

    Requirements are traceability anchors: they can be linked to the
    implementation work that realizes them (project tasks, Agile user stories,
    deliverables) without duplicating the standard Odoo execution model or the
    AMNUS Agile planning model.

    Approved versions are preserved as immutable snapshots in
    ``amnus.analysis.requirement.version``.
    """

    _name = "amnus.analysis.requirement"
    _description = "AMNUS Analysis Requirement"
    _inherit = ["mail.thread"]
    _order = "project_id, reference, id"
    _rec_name = "reference"

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Requirement Title",
        required=True,
        tracking=True,
        help="Short title of the requirement.",
    )
    reference = fields.Char(
        string="Requirement Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        help="Stable, human-readable requirement identifier (e.g. REQ-00001).",
    )
    description = fields.Text(string="Description", help="Detailed requirement description.")

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------
    requirement_type = fields.Selection(
        [
            ("business", "Business Requirement"),
            ("functional", "Functional Requirement"),
            ("non_functional", "Non-Functional Requirement"),
        ],
        string="Requirement Type",
        required=True,
        default="functional",
        tracking=True,
    )
    priority = fields.Selection(
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        string="Priority",
        default="medium",
        tracking=True,
        index=True,
    )
    business_value = fields.Text(
        string="Business Value",
        help="Business value delivered when this requirement is implemented.",
    )
    source = fields.Selection(
        [
            ("workshop", "Workshop"),
            ("interview", "Interview"),
            ("document", "Document"),
            ("email", "Email"),
            ("other", "Other"),
        ],
        string="Source",
        default="other",
        tracking=True,
        help="Origin of the requirement.",
    )
    acceptance_criteria = fields.Text(
        string="Acceptance Criteria",
        help="Criteria that must be satisfied for the requirement to be implemented.",
    )
    notes = fields.Text(string="Internal Notes")

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Implementation project this requirement belongs to.",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="project_id.partner_id",
        store=True,
        readonly=True,
        help="Customer of the project, derived from the project.",
    )
    stakeholder_id = fields.Many2one(
        "res.users",
        string="Primary Stakeholder",
        help="Primary customer stakeholder for this requirement.",
    )
    owner_id = fields.Many2one(
        "res.users",
        string="Business Owner",
        default=lambda self: self.env.user,
        tracking=True,
        help="Business owner responsible for the requirement.",
    )
    analyst_id = fields.Many2one(
        "res.users",
        string="Responsible Analyst",
        default=lambda self: self.env.user,
        tracking=True,
        help="Analyst responsible for eliciting and analyzing the requirement.",
    )
    target_stage_id = fields.Many2one(
        "project.project.stage",
        string="Target Project Stage",
        help="Target project stage / phase this requirement is planned for.",
    )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
        copy=False,
    )
    approval_notes = fields.Text(
        string="Approval Notes",
        help="Notes recorded during approval.",
    )
    rejected_by = fields.Many2one(
        "res.users",
        string="Rejected By",
        readonly=True,
        copy=False,
    )
    rejected_date = fields.Datetime(
        string="Rejected On",
        readonly=True,
        copy=False,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        help="Reason provided when rejecting the requirement.",
    )

    # ------------------------------------------------------------------
    # Traceability (optional links to implementation work)
    # ------------------------------------------------------------------
    task_id = fields.Many2one(
        "project.task",
        string="Linked Task",
        ondelete="set null",
        index=True,
        copy=False,
        help="Optional project task that implements this requirement.",
    )
    story_id = fields.Many2one(
        "amnus.agile.user.story",
        string="Linked User Story",
        ondelete="set null",
        index=True,
        copy=False,
        help="Optional Agile user story that plans this requirement.",
    )
    deliverable_id = fields.Many2one(
        "amnus.project.deliverable",
        string="Linked Deliverable",
        ondelete="set null",
        index=True,
        copy=False,
        help="Optional contractual deliverable that satisfies this requirement.",
    )

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------
    version_ids = fields.One2many(
        "amnus.analysis.requirement.version",
        "requirement_id",
        string="Approval Versions",
        readonly=True,
    )
    current_version = fields.Integer(
        string="Current Approved Version",
        readonly=True,
        copy=False,
        help="Version number of the most recently approved version (0 if never approved).",
    )

    # ------------------------------------------------------------------
    # Multi-company
    # ------------------------------------------------------------------
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Content fields (protected in approved/rejected/cancelled states)
    # ------------------------------------------------------------------
    CONTENT_FIELDS = {
        "name",
        "description",
        "requirement_type",
        "priority",
        "business_value",
        "source",
        "acceptance_criteria",
        "notes",
        "project_id",
        "stakeholder_id",
        "owner_id",
        "analyst_id",
        "target_stage_id",
        "task_id",
        "story_id",
        "deliverable_id",
    }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _requirement_reference_unique = models.Constraint(
        "unique (reference)",
        "Requirement reference must be unique.",
    )

    @api.constrains("task_id")
    def _check_task_project(self):
        """A linked task must belong to the same project as the requirement."""
        for requirement in self:
            if requirement.task_id and requirement.task_id.project_id != requirement.project_id:
                raise ValidationError(
                    _("The linked task must belong to the same project as the requirement.")
                )

    @api.constrains("story_id")
    def _check_story_project(self):
        """A linked Agile story must belong to the same project as the requirement."""
        for requirement in self:
            if requirement.story_id and requirement.story_id.project_id != requirement.project_id:
                raise ValidationError(
                    _("The linked user story must belong to the same project as the requirement.")
                )

    @api.constrains("deliverable_id")
    def _check_deliverable_project(self):
        """A linked deliverable must belong to the same project as the requirement."""
        for requirement in self:
            if (
                requirement.deliverable_id
                and requirement.deliverable_id.project_id != requirement.project_id
            ):
                raise ValidationError(
                    _("The linked deliverable must belong to the same project as the requirement.")
                )

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _is_analysis_manager(self):
        """Return whether the current user may manage AMNUS requirements."""
        return self.env.su or self.env.user.has_group(
            "amnus_analysis.group_amnus_analysis_manager"
        )

    def _check_is_analysis_manager(self):
        if not self._is_analysis_manager():
            raise UserError(_("Only an AMNUS Analysis Manager can perform this action."))

    # ------------------------------------------------------------------
    # Create / write / unlink
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Create requirements with a generated reference and draft state."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A requirement must be created in Draft state."))
            if vals.get("reference", _("New")) == _("New"):
                sequence = self.env["ir.sequence"].next_by_code("amnus.analysis.requirement")
                vals["reference"] = sequence or _("New")
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        """Protect lifecycle transitions, approval history, and content integrity.

        - Direct state writes are rejected (workflow-only).
        - Approval/rejection metadata is protected from direct writes.
        - Content fields are protected on approved/rejected/cancelled records
          (must use controlled revision).
        - project_id is protected on approved/rejected/cancelled records.
        """
        vals = dict(vals)
        # Direct state change: reject unless superuser (workflow path).
        if "state" in vals and not self.env.su:
            raise UserError(
                _("Requirement status cannot be changed directly. Use the workflow actions.")
            )
        # Protected approval/rejection metadata.
        protected = {"approved_by", "approved_date", "rejected_by", "rejected_date", "rejection_reason", "approval_notes", "current_version"}
        if set(vals) & protected and not self.env.su:
            raise UserError(_("Approval and rejection information cannot be modified directly."))
        # Content protection on protected states.
        if set(vals) & self.CONTENT_FIELDS and not self.env.su:
            for requirement in self:
                if requirement.state in ("approved", "rejected", "cancelled"):
                    raise UserError(
                        _("Requirement content cannot be modified in its current state. Use the revision workflow.")
                    )
        # Project protection on protected states.
        if "project_id" in vals and not self.env.su:
            for requirement in self:
                if requirement.state in ("approved", "rejected", "cancelled"):
                    raise UserError(
                        _("The project of an approved, rejected or cancelled requirement cannot be changed.")
                    )
                if requirement.task_id or requirement.story_id or requirement.deliverable_id:
                    raise UserError(
                        _("The project of a requirement with traceability links cannot be changed.")
                    )
        return super().write(vals)

    def unlink(self):
        """Protect approved, rejected and cancelled requirements from deletion."""
        for requirement in self:
            if requirement.state in ("approved", "rejected", "cancelled"):
                raise UserError(
                    _("Approved, rejected or cancelled requirements cannot be deleted. Archive them instead.")
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit_for_review(self):
        """Submit a draft requirement for review."""
        for requirement in self:
            if requirement.state != "draft":
                raise UserError(_("Only draft requirements can be submitted for review."))
        self._internal_write({"state": "under_review"})
        for requirement in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Requirement Submitted for Review"),
                action="state_change",
                description=_("Requirement %(ref)s submitted for review.", ref=requirement.reference),
                model_name=requirement._name,
                record_id=requirement.id,
            )
        return True

    def action_approve(self, approval_notes=None):
        """Approve a requirement under review and create an immutable version snapshot."""
        self._check_is_analysis_manager()
        for requirement in self:
            if requirement.state != "under_review":
                raise UserError(_("Only requirements under review can be approved."))
        # Lock to prevent concurrent version creation.
        self._lock_for_workflow()
        self.invalidate_recordset(["state", "current_version"])
        # Re-check state after lock.
        for requirement in self:
            if requirement.state != "under_review":
                raise UserError(_("Only requirements under review can be approved."))
        # Write approval state first (so version snapshot captures approved_by).
        self._internal_write(
            {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_date": fields.Datetime.now(),
                "approval_notes": approval_notes,
                "rejected_by": False,
                "rejected_date": False,
                "rejection_reason": False,
            }
        )
        # Create version snapshot after state change (captures approved_by).
        version_model = self.env["amnus.analysis.requirement.version"]
        for requirement in self:
            next_version = (requirement.current_version or 0) + 1
            version_model._create_from_requirement(requirement, next_version, approval_notes)
            requirement._internal_write({"current_version": next_version})
        for requirement in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Requirement Approved"),
                action="state_change",
                description=_("Requirement %(ref)s approved (version %(ver)s).", ref=requirement.reference, ver=requirement.current_version),
                model_name=requirement._name,
                record_id=requirement.id,
            )
        return True

    def action_reject(self, rejection_reason=None):
        """Reject a requirement under review (a reason is required)."""
        self._check_is_analysis_manager()
        for requirement in self:
            if requirement.state != "under_review":
                raise UserError(_("Only requirements under review can be rejected."))
        if not rejection_reason or not rejection_reason.strip():
            raise UserError(_("A rejection reason is required."))
        self._internal_write(
            {
                "state": "rejected",
                "rejected_by": self.env.user.id,
                "rejected_date": fields.Datetime.now(),
                "rejection_reason": rejection_reason.strip(),
                "approved_by": False,
                "approved_date": False,
                "approval_notes": False,
            }
        )
        for requirement in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Requirement Rejected"),
                action="state_change",
                description=_("Requirement %(ref)s rejected: %(reason)s.", ref=requirement.reference, reason=rejection_reason.strip()),
                model_name=requirement._name,
                record_id=requirement.id,
            )
        return True

    def action_cancel(self):
        """Cancel a draft or under-review requirement."""
        for requirement in self:
            if requirement.state not in ("draft", "under_review"):
                raise UserError(
                    _("Only draft or under-review requirements can be cancelled.")
                )
            if requirement.state == "under_review" and not self._is_analysis_manager():
                raise UserError(
                    _("Only an AMNUS Analysis Manager can cancel a requirement under review.")
                )
        self._internal_write({"state": "cancelled"})
        return True

    def action_request_revision(self):
        """Return an approved requirement to review for a controlled revision."""
        self._check_is_analysis_manager()
        for requirement in self:
            if requirement.state != "approved":
                raise UserError(_("Only approved requirements can be revised."))
        # Lock to prevent concurrent revision.
        self._lock_for_workflow()
        self.invalidate_recordset(["state", "current_version"])
        for requirement in self:
            if requirement.state != "approved":
                raise UserError(_("Only approved requirements can be revised."))
        # Clear previous approval metadata (preserved in version snapshot).
        self._internal_write(
            {
                "state": "under_review",
                "approved_by": False,
                "approved_date": False,
                "approval_notes": False,
            }
        )
        for requirement in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Requirement Revision Requested"),
                action="state_change",
                description=_("Requirement %(ref)s returned to review for revision.", ref=requirement.reference),
                model_name=requirement._name,
                record_id=requirement.id,
            )
        return True

    # ------------------------------------------------------------------
    # Internal write (bypass guards after validation)
    # ------------------------------------------------------------------
    def _internal_write(self, vals):
        """Write through the ORM parent after server-side validation.

        This is the only path allowed to mutate protected lifecycle fields.
        Callers MUST validate authorization and workflow preconditions before
        invoking it. It is private (RPC-inaccessible) and never exposed
        through a context flag.
        """
        return models.Model.write(self.sudo(), vals)

    def _lock_for_workflow(self):
        """Lock requirement rows to serialize version/metric changes."""
        if not self.ids:
            return
        self.env.cr.execute(
            "SELECT id FROM amnus_analysis_requirement WHERE id IN %s FOR UPDATE",
            (tuple(sorted(self.ids)),),
        )
