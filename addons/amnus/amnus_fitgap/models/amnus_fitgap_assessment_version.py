# -*- coding: utf-8 -*-
"""AMNUS Fit-Gap assessment version: immutable approval snapshot."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AmnusFitgapAssessmentVersion(models.Model):
    """Immutable snapshot of an approved Fit-Gap assessment."""

    _name = "amnus.fitgap.assessment.version"
    _description = "AMNUS Fit-Gap Assessment Version"
    _order = "assessment_id, version_number desc, id"
    _rec_name = "reference"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    assessment_id = fields.Many2one(
        "amnus.fitgap.assessment",
        string="Assessment",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
    )
    reference = fields.Char(
        string="Assessment Reference",
        related="assessment_id.reference",
        store=True,
        readonly=True,
    )
    version_number = fields.Integer(
        string="Version",
        required=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Approved content (immutable snapshot)
    # ------------------------------------------------------------------
    name = fields.Char(string="Assessment Title", readonly=True)
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
        readonly=True,
    )
    standard_odoo_module = fields.Char(string="Standard Odoo Module", readonly=True)
    standard_odoo_feature = fields.Char(string="Standard Odoo Feature", readonly=True)
    standard_behavior_description = fields.Text(string="Standard Behavior Description", readonly=True)
    gap_description = fields.Text(string="Gap Description", readonly=True)
    root_cause = fields.Text(string="Root Cause", readonly=True)
    business_impact = fields.Text(string="Business Impact", readonly=True)
    technical_impact = fields.Text(string="Technical Impact", readonly=True)
    configuration_approach = fields.Text(string="Configuration Approach", readonly=True)
    development_approach = fields.Text(string="Development Approach", readonly=True)
    integration_approach = fields.Text(string="Integration Approach", readonly=True)
    workaround_description = fields.Text(string="Workaround Description", readonly=True)
    proposed_solution = fields.Text(string="Proposed Solution", readonly=True)
    technical_notes = fields.Text(string="Technical Notes", readonly=True)
    dependencies = fields.Text(string="Dependencies", readonly=True)
    assumptions = fields.Text(string="Assumptions", readonly=True)
    functional_analysis_effort = fields.Float(string="Functional Analysis Effort (hours)", readonly=True)
    configuration_effort = fields.Float(string="Configuration Effort (hours)", readonly=True)
    development_effort = fields.Float(string="Development Effort (hours)", readonly=True)
    integration_effort = fields.Float(string="Integration Effort (hours)", readonly=True)
    testing_effort = fields.Float(string="Testing Effort (hours)", readonly=True)
    total_effort = fields.Float(string="Total Effort (hours)", readonly=True)
    estimation_confidence = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        string="Estimation Confidence",
        readonly=True,
    )
    risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        string="Risk Level",
        readonly=True,
    )
    decision_rationale = fields.Text(string="Decision Rationale", readonly=True)

    # ------------------------------------------------------------------
    # Context snapshots
    # ------------------------------------------------------------------
    requirement_reference = fields.Char(string="Requirement Reference (snapshot)", readonly=True)
    requirement_title = fields.Char(string="Requirement Title (snapshot)", readonly=True)
    project_name = fields.Char(string="Project Name (snapshot)", readonly=True)
    customer_name = fields.Char(string="Customer Name (snapshot)", readonly=True)

    # ------------------------------------------------------------------
    # Approval metadata
    # ------------------------------------------------------------------
    approved_by = fields.Many2one("res.users", string="Approved By", readonly=True, ondelete="set null")
    approved_date = fields.Datetime(string="Approved On", readonly=True)
    approval_notes = fields.Text(string="Approval Notes", readonly=True)

    # ------------------------------------------------------------------
    # Multi-company
    # ------------------------------------------------------------------
    company_id = fields.Many2one("res.company", string="Company", readonly=True, index=True)

    # ------------------------------------------------------------------
    # Immutability guards
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Versions are created only by the server-side approval workflow."""
        if not self.env.su:
            raise UserError(
                _("Assessment versions are created by the approval workflow and cannot be created manually.")
            )
        return super().create(vals_list)

    def write(self, vals):
        """Versions are immutable once created."""
        raise UserError(_("Assessment versions are immutable and cannot be modified."))

    def unlink(self):
        """Versions cannot be deleted."""
        raise UserError(_("Assessment versions cannot be deleted."))

    # ------------------------------------------------------------------
    # Server-side helpers
    # ------------------------------------------------------------------
    @api.model
    def _create_from_assessment(self, assessment, version_number, approval_notes=None):
        """Create an immutable snapshot from an assessment at approval time."""
        return self.sudo().create(
            {
                "assessment_id": assessment.id,
                "version_number": version_number,
                "name": assessment.name,
                "outcome": assessment.outcome,
                "standard_odoo_module": assessment.standard_odoo_module,
                "standard_odoo_feature": assessment.standard_odoo_feature,
                "standard_behavior_description": assessment.standard_behavior_description,
                "gap_description": assessment.gap_description,
                "root_cause": assessment.root_cause,
                "business_impact": assessment.business_impact,
                "technical_impact": assessment.technical_impact,
                "configuration_approach": assessment.configuration_approach,
                "development_approach": assessment.development_approach,
                "integration_approach": assessment.integration_approach,
                "workaround_description": assessment.workaround_description,
                "proposed_solution": assessment.proposed_solution,
                "technical_notes": assessment.technical_notes,
                "dependencies": assessment.dependencies,
                "assumptions": assessment.assumptions,
                "functional_analysis_effort": assessment.functional_analysis_effort,
                "configuration_effort": assessment.configuration_effort,
                "development_effort": assessment.development_effort,
                "integration_effort": assessment.integration_effort,
                "testing_effort": assessment.testing_effort,
                "total_effort": assessment.total_effort,
                "estimation_confidence": assessment.estimation_confidence,
                "risk_level": assessment.risk_level,
                "decision_rationale": assessment.decision_rationale,
                "requirement_reference": assessment.requirement_id.reference if assessment.requirement_id else False,
                "requirement_title": assessment.requirement_id.name if assessment.requirement_id else False,
                "project_name": assessment.project_id.name if assessment.project_id else False,
                "customer_name": assessment.customer_id.name if assessment.customer_id else False,
                "company_id": assessment.company_id.id if assessment.company_id else False,
                "approved_by": assessment.approved_by.id if assessment.approved_by else False,
                "approved_date": assessment.approved_date,
                "approval_notes": approval_notes,
            }
        )
