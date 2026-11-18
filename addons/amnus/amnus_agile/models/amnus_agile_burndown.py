# -*- coding: utf-8 -*-
"""AMNUS Agile burndown: historical scope/completion events per sprint."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

BURNDOWN_EVENT_TYPES = [
    ('baseline', 'Baseline'),
    ('scope_add', 'Scope Added'),
    ('scope_remove', 'Scope Removed'),
    ('reestimate', 'Re-estimation'),
    ('start', 'Work Started'),
    ('completion', 'Story Completed'),
    ('carry_over_out', 'Carried Over Out'),
    ('carry_over_in', 'Carried Over In'),
    ('cancellation', 'Cancellation'),
    ('closure', 'Sprint Closure'),
    ('update', 'Update'),
]


class AmnusAgileBurndown(models.Model):
    """AMNUS Agile burndown event: historical remaining/completed effort.

    Events are the historical source of truth for sprint scope and progress.
    They are created only by controlled server-side workflows and are immutable
    once recorded (no user/manager write or unlink). Chart rendering carries the
    last known value forward across event-free days.
    """

    _name = 'amnus.agile.burndown'
    _description = 'AMNUS Agile Burndown Event'
    _order = 'sprint_id, date, event_sequence, id'

    sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Sprint',
        required=True,
        ondelete='restrict',
        index=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='sprint_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='sprint_id.project_id',
        store=True,
        readonly=True,
        index=True,
    )
    story_id = fields.Many2one(
        'amnus.agile.user.story',
        string='User Story',
        ondelete='set null',
        readonly=True,
        index=True,
    )
    date = fields.Date(string='Date', required=True, readonly=True, index=True)
    event_type = fields.Selection(
        BURNDOWN_EVENT_TYPES,
        string='Event Type',
        required=True,
        readonly=True,
        default='update',
        index=True,
    )
    remaining_points = fields.Integer(string='Remaining (Story Points)', required=True, readonly=True)
    completed_points = fields.Integer(string='Completed (Story Points)', required=True, readonly=True)
    points_before = fields.Integer(string='Points Before', readonly=True)
    points_after = fields.Integer(string='Points After', readonly=True)
    event_sequence = fields.Integer(string='Event Sequence', readonly=True, default=0, index=True)

    _event_unique = models.Constraint(
        'unique (sprint_id, date, event_sequence)',
        'Burndown events must be uniquely ordered per sprint, date and sequence.',
    )

    @api.constrains('remaining_points', 'completed_points')
    def _check_values(self):
        for point in self:
            if point.remaining_points < 0 or point.completed_points < 0:
                raise ValidationError(_("Burndown points cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        # Only server-side workflows (sudo, internal) should create events.
        # Block direct creation by non-superuser callers to prevent fabricated history.
        if not self.env.su:
            raise UserError(
                _("Burndown history is managed by sprint workflows and cannot be created manually.")
            )
        return super().create(vals_list)

    def write(self, vals):
        # Immutable historical events.
        if not self.env.su:
            raise UserError(_("Burndown history is immutable and cannot be modified."))
        # Even superuser/internal code must not rewrite history; allow no-op safety.
        raise UserError(_("Burndown history is immutable and cannot be modified."))

    def unlink(self):
        if not self.env.su:
            raise UserError(_("Burndown history cannot be deleted."))
        raise UserError(_("Burndown history cannot be deleted."))
