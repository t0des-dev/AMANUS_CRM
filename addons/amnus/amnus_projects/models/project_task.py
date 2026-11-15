# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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

    def write(self, vals):
        """Preserve Agile story/task integrity when tasks are moved (F-02).

        A task linked to an AMNUS Agile user story must not be moved to another
        project or company while the link exists. This prevents broken cross-
        project relationships and cross-company disclosure through story fields.
        """
        if 'project_id' in vals and 'amnus.agile.user.story' in self.env:
            new_project = self.env['project.project'].browse(vals['project_id']) if vals['project_id'] else self.env['project.project']
            for task in self:
                story = self.env['amnus.agile.user.story'].sudo().search(
                    [('task_id', '=', task.id)], limit=1
                )
                if not story:
                    continue
                if not new_project:
                    raise UserError(
                        _("A task linked to an AMNUS Agile user story cannot be removed from its project.")
                    )
                # Project or company change breaks the invariant.
                if new_project != story.project_id or new_project.company_id != story.company_id:
                    raise UserError(
                        _("A task linked to an AMNUS Agile user story cannot be moved to another project or company.")
                    )
        return super().write(vals)
