# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AmnusAnalysisRequirementAgile(models.Model):
    """Optional Agile traceability for requirements."""

    _inherit = "amnus.analysis.requirement"

    story_id = fields.Many2one(
        "amnus.agile.user.story",
        string="Linked User Story",
        ondelete="set null",
        index=True,
        copy=False,
        help="Optional Agile user story that plans this requirement.",
    )

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

    @api.constrains("story_id")
    def _check_story_project(self):
        """A linked Agile story must belong to the same project as the requirement."""
        for requirement in self:
            if requirement.story_id and requirement.story_id.project_id != requirement.project_id:
                raise ValidationError(
                    _("The linked user story must belong to the same project as the requirement.")
                )
