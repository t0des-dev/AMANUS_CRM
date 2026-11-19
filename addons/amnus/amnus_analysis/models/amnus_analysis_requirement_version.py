# -*- coding: utf-8 -*-
"""AMNUS Analysis requirement version: immutable approval snapshot."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AmnusAnalysisRequirementVersion(models.Model):
    """Immutable snapshot of an approved requirement.

    Each version is created at approval time and captures the exact approved
    content. Versions are append-only: they cannot be created, modified, or
    deleted by ordinary users. Only the server-side approval workflow creates
    them (in sudo, after authorization).

    Related records are stored as both IDs and textual names so that the
    approved state can be reconstructed even if the related record changes or
    is deleted later.
    """

    _name = "amnus.analysis.requirement.version"
    _description = "AMNUS Analysis Requirement Version"
    _order = "requirement_id, version_number desc, id"
    _rec_name = "reference"

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    requirement_id = fields.Many2one(
        "amnus.analysis.requirement",
        string="Requirement",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
        help="The requirement this version belongs to.",
    )
    reference = fields.Char(
        string="Requirement Reference",
        related="requirement_id.reference",
        store=True,
        readonly=True,
    )
    version_number = fields.Integer(
        string="Version",
        required=True,
        readonly=True,
        help="Sequential version number within the requirement.",
    )

    # ------------------------------------------------------------------
    # Approved content (immutable snapshot)
    # ------------------------------------------------------------------
    name = fields.Char(string="Requirement Title", readonly=True)
    description = fields.Text(string="Description", readonly=True)
    requirement_type = fields.Selection(
        [
            ("business", "Business Requirement"),
            ("functional", "Functional Requirement"),
            ("non_functional", "Non-Functional Requirement"),
        ],
        string="Requirement Type",
        readonly=True,
    )
    priority = fields.Selection(
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        string="Priority",
        readonly=True,
    )
    business_value = fields.Text(string="Business Value", readonly=True)
    source = fields.Selection(
        [
            ("workshop", "Workshop"),
            ("interview", "Interview"),
            ("document", "Document"),
            ("email", "Email"),
            ("other", "Other"),
        ],
        string="Source",
        readonly=True,
    )
    acceptance_criteria = fields.Text(string="Acceptance Criteria", readonly=True)
    notes = fields.Text(string="Internal Notes", readonly=True)

    # ------------------------------------------------------------------
    # Related record snapshots (stored as both ID and text for immutability)
    # ------------------------------------------------------------------
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        readonly=True,
        ondelete="set null",
    )
    project_name = fields.Char(
        string="Project Name (snapshot)",
        readonly=True,
        help="Project name captured at approval time.",
    )
    customer_name = fields.Char(
        string="Customer Name (snapshot)",
        readonly=True,
        help="Customer name captured at approval time.",
    )
    stakeholder_id = fields.Many2one(
        "res.users",
        string="Primary Stakeholder",
        readonly=True,
        ondelete="set null",
    )
    stakeholder_name = fields.Char(
        string="Stakeholder Name (snapshot)",
        readonly=True,
    )
    owner_id = fields.Many2one(
        "res.users",
        string="Business Owner",
        readonly=True,
        ondelete="set null",
    )
    owner_name = fields.Char(
        string="Owner Name (snapshot)",
        readonly=True,
    )
    analyst_id = fields.Many2one(
        "res.users",
        string="Responsible Analyst",
        readonly=True,
        ondelete="set null",
    )
    analyst_name = fields.Char(
        string="Analyst Name (snapshot)",
        readonly=True,
    )
    target_stage_name = fields.Char(
        string="Target Stage (snapshot)",
        readonly=True,
    )
    task_reference = fields.Char(
        string="Linked Task Reference (snapshot)",
        readonly=True,
    )
    story_reference = fields.Char(
        string="Linked Story Reference (snapshot)",
        readonly=True,
    )
    deliverable_name = fields.Char(
        string="Linked Deliverable (snapshot)",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Approval metadata
    # ------------------------------------------------------------------
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        index=True,
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        ondelete="set null",
    )
    approved_date = fields.Datetime(
        string="Approved On",
        readonly=True,
    )
    approval_notes = fields.Text(
        string="Approval Notes",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Immutability guards
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Versions are created only by the server-side approval workflow."""
        if not self.env.su:
            raise UserError(
                _("Requirement versions are created by the approval workflow and cannot be created manually.")
            )
        return super().create(vals_list)

    def write(self, vals):
        """Versions are immutable once created."""
        raise UserError(_("Requirement versions are immutable and cannot be modified."))

    def unlink(self):
        """Versions cannot be deleted."""
        raise UserError(_("Requirement versions cannot be deleted."))

    # ------------------------------------------------------------------
    # Server-side helpers
    # ------------------------------------------------------------------
    @api.model
    def _create_from_requirement(self, requirement, version_number, approval_notes=None):
        """Create an immutable snapshot from a requirement at approval time.

        Must be called within the approval transaction (sudo context).
        """
        return self.sudo().create(
            {
                "requirement_id": requirement.id,
                "version_number": version_number,
                "name": requirement.name,
                "description": requirement.description,
                "requirement_type": requirement.requirement_type,
                "priority": requirement.priority,
                "business_value": requirement.business_value,
                "source": requirement.source,
                "acceptance_criteria": requirement.acceptance_criteria,
                "notes": requirement.notes,
                "project_id": requirement.project_id.id,
                "project_name": requirement.project_id.name if requirement.project_id else False,
                "customer_name": requirement.customer_id.name if requirement.customer_id else False,
                "stakeholder_id": requirement.stakeholder_id.id if requirement.stakeholder_id else False,
                "stakeholder_name": requirement.stakeholder_id.name if requirement.stakeholder_id else False,
                "owner_id": requirement.owner_id.id if requirement.owner_id else False,
                "owner_name": requirement.owner_id.name if requirement.owner_id else False,
                "analyst_id": requirement.analyst_id.id if requirement.analyst_id else False,
                "analyst_name": requirement.analyst_id.name if requirement.analyst_id else False,
                "target_stage_name": requirement.target_stage_id.name if requirement.target_stage_id else False,
                "task_reference": requirement.task_id.name if requirement.task_id else False,
                "story_reference": (
                    requirement.story_id.name
                    if "story_id" in requirement._fields and requirement.story_id
                    else False
                ),
                "deliverable_name": requirement.deliverable_id.name if requirement.deliverable_id else False,
                "company_id": requirement.company_id.id if requirement.company_id else False,
                "approved_by": requirement.approved_by.id if requirement.approved_by else False,
                "approved_date": requirement.approved_date,
                "approval_notes": approval_notes,
            }
        )
