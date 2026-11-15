# -*- coding: utf-8 -*-
"""AMNUS Agile burndown: historical remaining/completed effort per sprint date."""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AmnusAgileBurndown(models.Model):
    """AMNUS Agile burndown point: historical remaining/completed effort per sprint date.

    Burndown history is kept as dated metric snapshots derived from sprint events. Values
    are never fabricated retroactively; if no event is available for a date, no point is
    recorded for that date.
    """

    _name = 'amnus.agile.burndown'
    _description = 'AMNUS Agile Burndown'

    sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Sprint',
        required=True,
        ondelete='cascade',
    )
    date = fields.Date(string='Date', required=True)
    remaining_points = fields.Integer(string='Remaining (Story Points)', required=True)
    completed_points = fields.Integer(string='Completed (Story Points)', required=True)

    @api.constrains('remaining_points', 'completed_points')
    def _check_values(self):
        for point in self:
            if point.remaining_points < 0 or point.completed_points < 0:
                raise ValidationError(_("Burndown points cannot be negative."))
