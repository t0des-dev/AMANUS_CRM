# -*- coding: utf-8 -*-
"""AMNUS Fit-Gap assessment: assesses a requirement against standard Odoo capabilities."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusFitgapAssessment(models.Model):
    """AMNUS Fit-Gap assessment: assesses a requirement against standard Odoo.

    A Fit-Gap assessment documents how a business requirement maps to standard
    Odoo 19 Community functionality, identifies gaps, and records the recommended
    implementation approach (standard fit, configuration, custom development,
    integration, workaround, not supported, deferred, or requires further
    analysis).

    Assessments are linked to approved requirements and carry their own
    lifecycle (draft, in analysis, under review, approved, rejected, superseded,
    cancelled). Approved assessments are protected from silent rewrites and can
    only be changed through a controlled revision (new candidate assessment).

    Approved versions are preserved as immutable snapshots in
    ``amnus.fitgap.assessment.version``.
    """

    _name = "amnus.fitgap.assessment"
    _description = "AMNUS Fit-Gap Assessment"
    _inherit = ["mail.thread"]
    _order = "project_id, reference, id"
    _rec_name = "reference"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Assessment Title",
        required=True,
        tracking=True,
        help="Short title of the assessment.",
    )
    reference = fields.Char(
        string="Assessment Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        help="Stable, human-readable assessment identifier (e.g. FG-00001).",
    )

    # ------------------------------------------------------------------
    # Requirement relationship
    # ------------------------------------------------------------------
    requirement_id = fields.Many2one(
        "amnus.analysis.requirement",
        string="Requirement",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        domain="[('state', '=', 'approved')]",
        help="Approved requirement this assessment addresses.",
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        related="requirement_id.project_id",
        store=True,
        readonly=True,
        index=True,
        help="Implementation project, derived from the requirement.",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="project_id.partner_id",
        store=True,
        readonly=True,
        help="Customer of the project, derived from the project.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
        help="Company, derived from the project.",
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    assessor_id = fields.Many2one(
        "res.users",
        string="Assessor",
        default=lambda self: self.env.user,
        tracking=True,
        help="Analyst performing the assessment.",
    )
    reviewer_id = fields.Many2one(
        "res.users",
        string="Reviewer",
        tracking=True,
        help="Manager reviewing the assessment.",
    )
    assessment_date = fields.Date(
        string="Assessment Date",
        default=fields.Date.context_today,
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Classification (outcome)
    # ------------------------------------------------------------------
    outcome = fields.Selection(
        [
            ("standard_fit", "Standard Fit"),
            ("configuration", "Configuration"),
            ("custom_development", "Custom Development"),
            ("integration", "Integration"),
            ("workaround", "Workaround"),
            ("not_supported", "Not Supported"),
            ("deferred", "Deferred"),
            ("requires_analysis", "Requires Further Analysis"),
        ],
        string="Outcome",
        required=True,
        default="requires_analysis",
        tracking=True,
        help=_(
            "Implementation approach classification: standard fit, configuration, "
            "custom development, integration, workaround, not supported, deferred, "
            "or requires further analysis."
        ),
    )

    # ------------------------------------------------------------------
    # Standard Odoo capability reference (free-text, hybrid)
    # ------------------------------------------------------------------
    standard_odoo_module = fields.Char(
        string="Standard Odoo Module",
        help="Standard Odoo module that supports (or partially supports) the requirement (e.g. project, crm).",
    )
    standard_odoo_feature = fields.Char(
        string="Standard Odoo Feature",
        help="Standard Odoo feature that supports the requirement (e.g. Task stages, Kanban view).",
    )
    standard_behavior_description = fields.Text(
        string="Standard Behavior Description",
        help="How standard Odoo supports (or does not support) the requirement.",
    )

    # ------------------------------------------------------------------
    # Gap analysis
    # ------------------------------------------------------------------
    gap_description = fields.Text(
        string="Gap Description",
        help="Description of the gap between the requirement and standard Odoo.",
    )
    root_cause = fields.Text(
        string="Root Cause",
        help="Why the gap exists (standard limitation, missing feature, etc.).",
    )
    business_impact = fields.Text(
        string="Business Impact",
        help="Impact on the business if the gap is not addressed.",
    )
    technical_impact = fields.Text(
        string="Technical Impact",
        help="Technical impact of the proposed approach.",
    )

    # ------------------------------------------------------------------
    # Implementation approach
    # ------------------------------------------------------------------
    configuration_approach = fields.Text(
        string="Configuration Approach",
        help="Configuration steps needed.",
    )
    development_approach = fields.Text(
        string="Development Approach",
        help="Custom development needed.",
    )
    integration_approach = fields.Text(
        string="Integration Approach",
        help="Integration requirements.",
    )
    workaround_description = fields.Text(
        string="Workaround Description",
        help="Alternative process description.",
    )
    proposed_solution = fields.Text(
        string="Proposed Solution",
        help="Proposed implementation solution.",
    )
    technical_notes = fields.Text(
        string="Technical Notes",
        help="Technical notes.",
    )
    dependencies = fields.Text(
        string="Dependencies",
        help="Dependencies on other requirements or modules.",
    )
    assumptions = fields.Text(
        string="Assumptions",
        help="Assumptions made during assessment.",
    )

    # ------------------------------------------------------------------
    # Effort estimation (5 categories, computed total)
    # ------------------------------------------------------------------
    functional_analysis_effort = fields.Float(
        string="Functional Analysis Effort (hours)",
        default=0.0,
        help="Requirements analysis and design effort.",
    )
    configuration_effort = fields.Float(
        string="Configuration Effort (hours)",
        default=0.0,
        help="Configuration and setup effort.",
    )
    development_effort = fields.Float(
        string="Development Effort (hours)",
        default=0.0,
        help="Custom development effort.",
    )
    integration_effort = fields.Float(
        string="Integration Effort (hours)",
        default=0.0,
        help="Integration development effort.",
    )
    testing_effort = fields.Float(
        string="Testing Effort (hours)",
        default=0.0,
        help="Testing effort.",
    )
    total_effort = fields.Float(
        string="Total Effort (hours)",
        compute="_compute_total_effort",
        store=True,
        readonly=True,
        help="Sum of all effort categories.",
    )
    estimation_confidence = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Estimation Confidence",
        default="medium",
        tracking=True,
    )
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Risk Level",
        default="medium",
        tracking=True,
    )

    # ------------------------------------------------------------------
    # Decision and approval metadata
    # ------------------------------------------------------------------
    decision_rationale = fields.Text(
        string="Decision Rationale",
        help="Rationale for the implementation decision.",
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
        help="Reason provided when rejecting the assessment.",
    )
    revision_notes = fields.Text(
        string="Revision Notes",
        help="Notes on revision.",
    )

    # ------------------------------------------------------------------
    # Evidence
    # ------------------------------------------------------------------
    evidence_ids = fields.Many2many(
        "ir.attachment",
        string="Evidence",
        help="Evidence attachments (screenshots, documentation references, etc.).",
    )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_analysis", "In Analysis"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("superseded", "Superseded"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Current assessment marker
    # ------------------------------------------------------------------
    is_current = fields.Boolean(
        string="Current Assessment",
        default=False,
        index=True,
        copy=False,
        help="Whether this is the current (authoritative) assessment for the requirement.",
    )

    # ------------------------------------------------------------------
    # Version history
    # ------------------------------------------------------------------
    version_ids = fields.One2many(
        "amnus.fitgap.assessment.version",
        "assessment_id",
        string="Assessment Versions",
        readonly=True,
    )
    current_version = fields.Integer(
        string="Current Approved Version",
        readonly=True,
        copy=False,
        help="Version number of the most recently approved version (0 if never approved).",
    )

    # ------------------------------------------------------------------
    # Content fields (protected in approved/rejected/cancelled/superseded states)
    # ------------------------------------------------------------------
    CONTENT_FIELDS = {
        "name",
        "requirement_id",
        "outcome",
        "standard_odoo_module",
        "standard_odoo_feature",
        "standard_behavior_description",
        "gap_description",
        "root_cause",
        "business_impact",
        "technical_impact",
        "configuration_approach",
        "development_approach",
        "integration_approach",
        "workaround_description",
        "proposed_solution",
        "technical_notes",
        "dependencies",
        "assumptions",
        "functional_analysis_effort",
        "configuration_effort",
        "development_effort",
        "integration_effort",
        "testing_effort",
        "estimation_confidence",
        "risk_level",
        "decision_rationale",
        "evidence_ids",
        "assessor_id",
        "reviewer_id",
        "assessment_date",
    }

    # ------------------------------------------------------------------
    # Database-level partial unique index (current assessment invariant)
    # ------------------------------------------------------------------
    def init(self):
        """Create the partial unique index enforcing one current assessment per requirement.

        PostgreSQL table constraints cannot express a partial uniqueness
        condition, so the invariant is enforced through a partial unique
        index created here (and re-created idempotently on every module
        load). The index covers only rows where ``is_current`` is TRUE.
        """
        super().init()
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
                amnus_fitgap_assessment_current_unique
            ON amnus_fitgap_assessment (requirement_id)
            WHERE is_current = TRUE
            """
        )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    _assessment_reference_unique = models.Constraint(
        "unique (reference)",
        "Assessment reference must be unique.",
    )

    @api.constrains("requirement_id")
    def _check_requirement_approved(self):
        """Assessment can only be created for approved requirements."""
        for assessment in self:
            if assessment.requirement_id and assessment.requirement_id.state != "approved":
                raise ValidationError(
                    _("A Fit-Gap assessment can only be created for an approved requirement.")
                )

    @api.constrains("requirement_id", "company_id")
    def _check_company_consistency(self):
        """Assessment must belong to the same company as the requirement."""
        for assessment in self:
            if assessment.requirement_id and assessment.company_id:
                if assessment.requirement_id.company_id != assessment.company_id:
                    raise ValidationError(
                        _("The assessment company must match the requirement company.")
                    )

    @api.constrains("functional_analysis_effort", "configuration_effort",
                    "development_effort", "integration_effort", "testing_effort")
    def _check_effort_non_negative(self):
        """Effort values must be non-negative."""
        for assessment in self:
            for field_name in ("functional_analysis_effort", "configuration_effort",
                               "development_effort", "integration_effort", "testing_effort"):
                if getattr(assessment, field_name) < 0:
                    raise ValidationError(_("Effort values cannot be negative."))

    # ------------------------------------------------------------------
    # Computed fields
    # ------------------------------------------------------------------
    @api.depends("functional_analysis_effort", "configuration_effort",
                 "development_effort", "integration_effort", "testing_effort")
    def _compute_total_effort(self):
        for assessment in self:
            assessment.total_effort = (
                (assessment.functional_analysis_effort or 0.0)
                + (assessment.configuration_effort or 0.0)
                + (assessment.development_effort or 0.0)
                + (assessment.integration_effort or 0.0)
                + (assessment.testing_effort or 0.0)
            )

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _is_fitgap_manager(self):
        """Return whether the current user may manage Fit-Gap assessments."""
        return self.env.su or self.env.user.has_group("amnus_fitgap.group_amnus_fitgap_manager")

    def _check_is_fitgap_manager(self):
        if not self._is_fitgap_manager():
            raise UserError(_("Only an AMNUS Fit-Gap Manager can perform this action."))

    # ------------------------------------------------------------------
    # Create / write / unlink
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Create assessments with a generated reference and draft state."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("state", "draft") != "draft":
                raise UserError(_("A Fit-Gap assessment must be created in Draft state."))
            if vals.get("reference", _("New")) == _("New"):
                sequence = self.env["ir.sequence"].next_by_code("amnus.fitgap.assessment")
                vals["reference"] = sequence or _("New")
            # Validate requirement is approved
            if vals.get("requirement_id"):
                requirement = self.env["amnus.analysis.requirement"].browse(vals["requirement_id"])
                if requirement.state != "approved":
                    raise ValidationError(
                        _("A Fit-Gap assessment can only be created for an approved requirement.")
                    )
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        """Protect lifecycle transitions, approval history, and content integrity."""
        vals = dict(vals)
        # Reference is a stable business identifier and cannot be changed.
        if "reference" in vals and not self.env.su:
            raise UserError(_("Assessment reference cannot be modified."))
        # Direct state change: reject unless superuser.
        if "state" in vals and not self.env.su:
            raise UserError(
                _("Assessment status cannot be changed directly. Use the workflow actions.")
            )
        # Protected approval/rejection metadata.
        protected = {"approved_by", "approved_date", "rejected_by", "rejected_date",
                     "rejection_reason", "approval_notes", "current_version", "is_current"}
        if set(vals) & protected and not self.env.su:
            raise UserError(_("Approval and rejection information cannot be modified directly."))
        # Content protection on protected states.
        if set(vals) & self.CONTENT_FIELDS and not self.env.su:
            for assessment in self:
                if assessment.state in ("approved", "rejected", "cancelled", "superseded"):
                    raise UserError(
                        _("Assessment content cannot be modified in its current state. Use the revision workflow.")
                    )
        # Project protection (project is derived, but guard against direct changes).
        if "project_id" in vals and not self.env.su:
            for assessment in self:
                if assessment.state in ("approved", "rejected", "cancelled", "superseded"):
                    raise UserError(
                        _("The project of an approved, rejected, cancelled or superseded assessment cannot be changed.")
                    )
        return super().write(vals)

    def unlink(self):
        """Protect approved, rejected, cancelled and superseded assessments from deletion."""
        for assessment in self:
            if assessment.state in ("approved", "rejected", "cancelled", "superseded"):
                raise UserError(
                    _("Approved, rejected, cancelled or superseded assessments cannot be deleted. Archive them instead.")
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_start_analysis(self):
        """Move a draft assessment to in-analysis."""
        for assessment in self:
            if assessment.state != "draft":
                raise UserError(_("Only draft assessments can be moved to analysis."))
        self._lock_for_workflow()
        self.invalidate_recordset(["state"])
        for assessment in self:
            if assessment.state != "draft":
                raise UserError(_("Only draft assessments can be moved to analysis."))
        self._internal_write({"state": "in_analysis"})
        for assessment in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Analysis Started"),
                action="state_change",
                description=_("Assessment %(ref)s moved to analysis.", ref=assessment.reference),
                model_name=assessment._name,
                record_id=assessment.id,
            )
        return True

    def action_submit_for_review(self):
        """Submit an assessment for review."""
        for assessment in self:
            if assessment.state not in ("draft", "in_analysis"):
                raise UserError(_("Only draft or in-analysis assessments can be submitted for review."))
        self._lock_for_workflow()
        self.invalidate_recordset(["state"])
        for assessment in self:
            if assessment.state not in ("draft", "in_analysis"):
                raise UserError(_("Only draft or in-analysis assessments can be submitted for review."))
        self._internal_write({"state": "under_review"})
        for assessment in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Submitted for Review"),
                action="state_change",
                description=_("Assessment %(ref)s submitted for review.", ref=assessment.reference),
                model_name=assessment._name,
                record_id=assessment.id,
            )
        return True

    def action_approve(self, approval_notes=None):
        """Approve an assessment under review and create an immutable version snapshot."""
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "under_review":
                raise UserError(_("Only assessments under review can be approved."))
        # Lock to prevent concurrent version creation.
        self._lock_for_workflow()
        self.invalidate_recordset(["state", "current_version", "is_current"])
        # Revalidate authorization and state after lock.
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "under_review":
                raise UserError(_("Only assessments under review can be approved."))
        # Supersede previous current assessment (if any) before promoting the
        # new one, so the partial unique index is never violated.
        for assessment in self:
            previous = self.env["amnus.fitgap.assessment"].search([
                ("requirement_id", "=", assessment.requirement_id.id),
                ("is_current", "=", True),
                ("id", "!=", assessment.id),
            ])
            for prev in previous:
                prev._internal_write({"is_current": False, "state": "superseded"})
        # Write approval state and promote the new assessment to current.
        approval_vals = {
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_date": fields.Datetime.now(),
            "rejected_by": False,
            "rejected_date": False,
            "rejection_reason": False,
            "is_current": True,
        }
        if approval_notes is not None:
            approval_vals["approval_notes"] = approval_notes
        self._internal_write(approval_vals)
        # Create version snapshot after state change.
        version_model = self.env["amnus.fitgap.assessment.version"]
        for assessment in self:
            next_version = (assessment.current_version or 0) + 1
            version_model._create_from_assessment(
                assessment, next_version,
                approval_notes if approval_notes is not None else assessment.approval_notes,
            )
            assessment._internal_write({"current_version": next_version})
        for assessment in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Approved"),
                action="state_change",
                description=_("Assessment %(ref)s approved (version %(ver)s).", ref=assessment.reference, ver=assessment.current_version),
                model_name=assessment._name,
                record_id=assessment.id,
            )
        return True

    def action_reject(self, rejection_reason=None):
        """Reject an assessment under review (a reason is required)."""
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "under_review":
                raise UserError(_("Only assessments under review can be rejected."))
        self._lock_for_workflow()
        self.invalidate_recordset(["state", "rejection_reason"])
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "under_review":
                raise UserError(_("Only assessments under review can be rejected."))
        reasons = []
        for assessment in self:
            reason = rejection_reason if rejection_reason is not None else assessment.rejection_reason
            if not reason or not str(reason).strip():
                raise UserError(_("A rejection reason is required."))
            reasons.append(str(reason).strip())
        for assessment, reason in zip(self, reasons):
            assessment._internal_write(
                {
                    "state": "rejected",
                    "rejected_by": self.env.user.id,
                    "rejected_date": fields.Datetime.now(),
                    "rejection_reason": reason,
                    "approved_by": False,
                    "approved_date": False,
                    "approval_notes": False,
                }
            )
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Rejected"),
                action="state_change",
                description=_("Assessment %(ref)s rejected: %(reason)s.", ref=assessment.reference, reason=reason),
                model_name=assessment._name,
                record_id=assessment.id,
            )
        return True

    def action_open_reject_wizard(self):
        """Open the native wizard used to collect a rejection reason."""
        self.ensure_one()
        if self.state != "under_review":
            raise UserError(_("Only assessments under review can be rejected."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Assessment"),
            "res_model": "amnus.fitgap.assessment.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_assessment_id": self.id},
        }

    def action_cancel(self):
        """Cancel a draft, in-analysis, or under-review assessment."""
        for assessment in self:
            if assessment.state not in ("draft", "in_analysis", "under_review"):
                raise UserError(
                    _("Only draft, in-analysis or under-review assessments can be cancelled.")
                )
            if assessment.state == "under_review" and not self._is_fitgap_manager():
                raise UserError(
                    _("Only an AMNUS Fit-Gap Manager can cancel an assessment under review.")
                )
        self._lock_for_workflow()
        self.invalidate_recordset(["state"])
        for assessment in self:
            if assessment.state not in ("draft", "in_analysis", "under_review"):
                raise UserError(
                    _("Only draft, in-analysis or under-review assessments can be cancelled.")
                )
            if assessment.state == "under_review" and not self._is_fitgap_manager():
                raise UserError(
                    _("Only an AMNUS Fit-Gap Manager can cancel an assessment under review.")
                )
        self._internal_write({"state": "cancelled"})
        for assessment in self:
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Cancelled"),
                action="state_change",
                description=_("Assessment %(ref)s cancelled.", ref=assessment.reference),
                model_name=assessment._name,
                record_id=assessment.id,
            )
        return True

    def action_request_revision(self):
        """Create a non-current candidate assessment revising an approved one.

        The previously approved assessment remains immutable and current until
        the candidate is approved; revision never mutates the approved record.
        """
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "approved":
                raise UserError(_("Only approved assessments can be revised."))
        self._lock_for_workflow()
        self.invalidate_recordset(["state", "is_current"])
        self._check_is_fitgap_manager()
        for assessment in self:
            if assessment.state != "approved":
                raise UserError(_("Only approved assessments can be revised."))
        created = self.env["amnus.fitgap.assessment"]
        content_fields = [
            "name", "outcome", "standard_odoo_module", "standard_odoo_feature",
            "standard_behavior_description", "gap_description", "root_cause",
            "business_impact", "technical_impact", "configuration_approach",
            "development_approach", "integration_approach",
            "workaround_description", "proposed_solution", "technical_notes",
            "dependencies", "assumptions", "functional_analysis_effort",
            "configuration_effort", "development_effort", "integration_effort",
            "testing_effort", "estimation_confidence", "risk_level",
            "decision_rationale", "evidence_ids", "assessor_id", "reviewer_id",
        ]
        for assessment in self:
            vals = {
                "requirement_id": assessment.requirement_id.id,
                "revision_notes": _("Revision of %(ref)s.", ref=assessment.reference),
            }
            for field_name in content_fields:
                field = self._fields[field_name]
                value = assessment[field_name]
                if field.type == "many2many":
                    vals[field_name] = [(6, 0, value.ids)]
                elif field.type in ("many2one",):
                    vals[field_name] = value.id if value else False
                else:
                    vals[field_name] = value
            candidate = self.env["amnus.fitgap.assessment"].create(vals)
            created |= candidate
            self.env["amnus.audit.log"]._log_event(
                name=_("Assessment Revision Candidate Created"),
                action="create",
                description=_("Revision candidate %(ref)s created from %(old)s.", ref=candidate.reference, old=assessment.reference),
                model_name=candidate._name,
                record_id=candidate.id,
            )
        if len(created) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Revision Candidate"),
                "res_model": "amnus.fitgap.assessment",
                "res_id": created.id,
                "view_mode": "form",
                "target": "current",
            }
        return True

    # ------------------------------------------------------------------
    # Internal write (bypass guards after validation)
    # ------------------------------------------------------------------
    def _internal_write(self, vals):
        """Write through the ORM parent after server-side validation."""
        return models.Model.write(self.sudo(), vals)

    def _lock_for_workflow(self):
        """Lock requirement and all assessment rows to serialize workflow changes."""
        requirement_ids = sorted({r.id for r in self.mapped("requirement_id") if r})
        if not requirement_ids:
            return
        self.env.cr.execute(
            "SELECT id FROM amnus_analysis_requirement WHERE id IN %s FOR UPDATE",
            (tuple(requirement_ids),),
        )
        self.env.cr.execute(
            "SELECT id FROM amnus_fitgap_assessment WHERE requirement_id IN %s FOR UPDATE",
            (tuple(requirement_ids),),
        )
