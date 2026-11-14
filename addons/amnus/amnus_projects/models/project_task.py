# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    """AMNUS extension for standard project tasks.

    Only the optional deliverable link is added. Task states, stages,
    assignees, deadlines and visibility remain standard Odoo behavior.
    """

    _inherit = "project.task"

    amnus_deliverable_id = fields.Many2one(
        "amnus.project.deliverable",
        string="Deliverable",
        ondelete="set null",
        index=True,
        copy=False,
        domain="[('project_id', '=', project_id)]",
        help="Deliverable this task contributes to (optional).",
    )

    @api.constrains("amnus_deliverable_id", "project_id")
    def _check_amnus_deliverable_project(self):
        for task in self:
            if not task.amnus_deliverable_id:
                continue
            if task.amnus_deliverable_id.project_id != task.project_id:
                raise ValidationError(
                    _("The deliverable must belong to the same project as the task.")
                )
