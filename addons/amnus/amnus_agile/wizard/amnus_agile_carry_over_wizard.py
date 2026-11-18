# -*- coding: utf-8 -*-
"""AMNUS Agile carry-over wizard: move unfinished stories to another sprint."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AmnusAgileCarryOverWizard(models.TransientModel):
    """Explicit carry-over action with authorization and audit trail."""

    _name = 'amnus.agile.carry.over.wizard'
    _description = 'AMNUS Agile Sprint Carry-Over'

    sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Source Sprint',
        required=True,
        readonly=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='sprint_id.project_id',
        readonly=True,
    )
    target_sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Destination Sprint',
        required=True,
        domain="[('project_id', '=', project_id), "
               "('id', '!=', sprint_id), "
               "('state', 'in', ['draft', 'planned', 'active'])]",
    )
    story_ids = fields.Many2many(
        'amnus.agile.user.story',
        string='Unfinished Stories',
        domain="[('sprint_id', '=', sprint_id), ('state', 'not in', ['done', 'cancelled'])]",
    )
    reason = fields.Text(string='Carry-Over Reason')

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        sprint_id = self.env.context.get('active_id')
        if sprint_id and 'sprint_id' in fields_list:
            sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
            if sprint.exists():
                values['sprint_id'] = sprint.id
                if 'story_ids' in fields_list:
                    values['story_ids'] = [(6, 0, sprint.story_ids.filtered(
                        lambda story: story.state not in ('done', 'cancelled')
                    ).ids)]
        return values

    def action_carry_over(self):
        """Execute the carry-over on the source sprint."""
        self.ensure_one()
        if not self.story_ids:
            raise UserError(_("Select at least one unfinished user story."))
        self.sprint_id.action_carry_over(
            self.story_ids.ids,
            self.target_sprint_id.id,
            reason=self.reason,
        )
        return {'type': 'ir.actions.act_window_close'}
