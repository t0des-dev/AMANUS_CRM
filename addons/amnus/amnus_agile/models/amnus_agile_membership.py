# -*- coding: utf-8 -*-
"""AMNUS Agile sprint membership history.

Membership rows are the historical source of truth for which user stories were
committed to a sprint, at which Story Points, and how they left the sprint
(completed, carried over, removed or cancelled). Rows are append-only from the
user interface: access rules forbid creating, writing or deleting them directly.
Only server-side sprint/story workflows (running in ``sudo``) may change them.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

MEMBERSHIP_OUTCOMES = [
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('incomplete', 'Incomplete at Closure'),
    ('carried_over', 'Carried Over'),
    ('removed', 'Removed from Sprint'),
    ('cancelled', 'Cancelled'),
]
"""Terminal outcomes of a sprint membership row."""


class AmnusAgileSprintMembership(models.Model):
    """Historical membership of one user story in one sprint."""

    _name = 'amnus.agile.sprint.membership'
    _description = 'AMNUS Agile Sprint Membership'
    _order = 'sprint_id, date_added, id'

    sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Sprint',
        required=True,
        ondelete='cascade',
        index=True,
    )
    story_id = fields.Many2one(
        'amnus.agile.user.story',
        string='User Story',
        required=True,
        ondelete='cascade',
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
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='sprint_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    date_added = fields.Datetime(
        string='Added On',
        default=fields.Datetime.now,
        readonly=True,
        required=True,
    )
    added_by_id = fields.Many2one(
        'res.users',
        string='Added By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    date_removed = fields.Datetime(string='Removed On', readonly=True)
    removed_by_id = fields.Many2one('res.users', string='Removed By', readonly=True)
    committed_points = fields.Integer(
        string='Original Story Points',
        readonly=True,
        help="Story Points captured when the story entered the sprint commitment.",
    )
    final_points = fields.Integer(
        string='Final Story Points',
        readonly=True,
        help="Story Points captured when the membership ended.",
    )
    outcome = fields.Selection(
        MEMBERSHIP_OUTCOMES,
        string='Outcome',
        default='active',
        required=True,
        readonly=True,
        index=True,
    )
    carry_over_sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Carried Over To',
        readonly=True,
        ondelete='set null',
    )
    reason = fields.Text(string='Reason', readonly=True)

    _sprint_story_unique = models.Constraint(
        'unique (sprint_id, story_id)',
        'A user story can only have one membership record per sprint.',
    )

    @api.constrains('sprint_id', 'story_id')
    def _check_membership_consistency(self):
        """Reject memberships that cross projects or companies."""
        for membership in self:
            story = membership.story_id
            sprint = membership.sprint_id
            if story.project_id != sprint.project_id or story.company_id != sprint.company_id:
                raise ValidationError(
                    _(
                        "A sprint membership must link a story and a sprint of the "
                        "same project and company."
                    )
                )

    @api.constrains('story_id', 'outcome', 'date_removed')
    def _check_single_open_membership(self):
        """A story may only have one open membership at a time."""
        for membership in self:
            if membership.outcome != 'active' or membership.date_removed:
                continue
            duplicates = self.sudo().search_count([
                ('story_id', '=', membership.story_id.id),
                ('outcome', '=', 'active'),
                ('date_removed', '=', False),
                ('id', '!=', membership.id),
            ])
            if duplicates:
                raise ValidationError(
                    _("A user story cannot belong to two sprints at the same time.")
                )

    # ------------------------------------------------------------------
    # ORM guards: membership history is append-only and workflow-controlled
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise UserError(
                _("Sprint membership history is managed by workflows and cannot be created manually.")
            )
        return super().create(vals_list)

    def write(self, vals):
        # Only internal server-side workflow code may mutate memberships.
        # Once closed (date_removed set), rows are immutable.
        if not self.env.su:
            raise UserError(
                _("Sprint membership history is managed by workflows and cannot be modified manually.")
            )
        for membership in self:
            if membership.date_removed and membership.outcome != 'active':
                raise UserError(
                    _("Closed sprint membership history cannot be rewritten.")
                )
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(_("Sprint membership history cannot be deleted."))
        raise UserError(_("Sprint membership history cannot be deleted."))

    # ------------------------------------------------------------------
    # Server-side helpers (called from story / sprint workflows in sudo)
    # ------------------------------------------------------------------
    def _close(self, outcome, carry_over_sprint=None, reason=None):
        """Close the membership with a terminal outcome.

        ``outcome`` is one of the non-active selection values. The row is never
        deleted, so sprint history remains reconstructable. Closed rows are
        immutable after this operation.
        """
        for membership in self:
            if membership.date_removed:
                raise UserError(
                    _("Closed sprint membership history cannot be rewritten.")
                )
            values = {
                'outcome': outcome,
                'date_removed': fields.Datetime.now(),
                'removed_by_id': self.env.user.id,
                'final_points': membership.story_id.story_points or 0,
            }
            if carry_over_sprint:
                values['carry_over_sprint_id'] = carry_over_sprint.id
            if reason:
                values['reason'] = reason
            super(AmnusAgileSprintMembership, membership.sudo()).write(values)
        return True

    def _mark_committed(self, points=None):
        """Refresh the committed Story Points snapshot of an open membership."""
        for membership in self:
            if membership.date_removed or membership.outcome != 'active':
                raise UserError(
                    _("Closed sprint membership history cannot be rewritten.")
                )
            super(AmnusAgileSprintMembership, membership.sudo()).write({
                'committed_points': (
                    membership.story_id.story_points or 0
                    if points is None
                    else points
                ),
            })
        return True
