# -*- coding: utf-8 -*-
"""AMNUS Agile sprint: a time-boxed planning iteration of user stories."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

SPRINT_STATES = ('draft', 'planned', 'active', 'closed', 'cancelled')

SPRINT_ALLOWED_TRANSITIONS = {
    'draft': ('planned', 'cancelled'),
    'planned': ('active', 'cancelled'),
    'active': ('closed', 'cancelled'),
    'closed': (),
    'cancelled': (),
}
"""Sprint lifecycle transitions. Closed sprints can never be reopened."""


class AmnusAgileSprint(models.Model):
    """AMNUS Agile sprint: a time-boxed planning iteration of user stories.

    A sprint owns the backlog membership, capacity, commitment, completion figures and
    burndown history for a single Agile iteration. The historical metrics are computed
    from dated story events; nothing is fabricated retroactively.
    """

    _name = 'amnus.agile.sprint'
    _description = 'AMNUS Agile Sprint'
    _order = 'project_id, date_start, id'

    name = fields.Char(string='Sprint Name', required=True)
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='project_id.company_id',
        store=True,
        readonly=True,
        index=True,
    )
    goal = fields.Text(string='Sprint Goal')
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('planned', 'Planned'),
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled'),
        ],
        string='State',
        default='draft',
        required=True,
        index=True,
        copy=False,
    )
    story_ids = fields.One2many(
        'amnus.agile.user.story',
        'sprint_id',
        string='Sprint Backlog',
    )
    capacity_points = fields.Integer(string='Capacity (Story Points)')
    committed_points = fields.Integer(
        string='Committed (Story Points)',
        compute='_compute_sprint_metrics',
        readonly=True,
        store=True,
    )
    completed_points = fields.Integer(
        string='Completed (Story Points)',
        compute='_compute_sprint_metrics',
        readonly=True,
        store=True,
    )
    carry_over_points = fields.Integer(
        string='Carry Over (Story Points)',
        compute='_compute_sprint_metrics',
        readonly=True,
        store=True,
    )
    baseline_points = fields.Integer(
        string='Baseline Commitment (Story Points)',
        readonly=True,
        copy=False,
        help="Committed Story Points captured when the sprint was activated.",
    )
    final_committed_points = fields.Integer(
        string='Final Committed (Story Points)',
        readonly=True,
        copy=False,
        help="Committed Story Points frozen when the sprint was closed or cancelled.",
    )
    final_completed_points = fields.Integer(
        string='Final Completed (Story Points)',
        readonly=True,
        copy=False,
        help="Completed Story Points frozen when the sprint was closed or cancelled.",
    )
    final_carry_over_points = fields.Integer(
        string='Final Carry Over (Story Points)',
        readonly=True,
        copy=False,
        help="Unfinished Story Points frozen when the sprint was closed or cancelled.",
    )
    velocity_points = fields.Integer(
        string='Velocity (Story Points)',
        compute='_compute_velocity_points',
        readonly=True,
        store=True,
        help="Completed Story Points counted for velocity once the sprint is closed.",
    )
    membership_ids = fields.One2many(
        'amnus.agile.sprint.membership',
        'sprint_id',
        string='Membership History',
        readonly=True,
    )
    review_summary = fields.Text(string='Review Summary')
    review_accepted_outcomes = fields.Text(string='Accepted Outcomes')
    review_incomplete_work = fields.Text(string='Incomplete Work')
    retrospective_observations = fields.Text(string='Retrospective Observations')
    retro_went_well = fields.Text(string='What Went Well')
    retro_did_not_go_well = fields.Text(string='What Did Not Go Well')
    improvement_actions = fields.Text(string='Improvement Actions')
    action_owner_id = fields.Many2one(
        'res.users',
        string='Improvement Action Owner',
    )
    action_target_date = fields.Date(string='Improvement Action Target Date')
    active = fields.Boolean(string='Active', default=True)
    burndown_point_ids = fields.One2many(
        'amnus.agile.burndown',
        'sprint_id',
        string='Burndown',
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for sprint in self:
            if sprint.date_start and sprint.date_end and sprint.date_end < sprint.date_start:
                raise ValidationError(_("The sprint end date cannot be before the start date."))

    def write(self, vals):
        """Guard lifecycle transitions and protect historical figures."""
        if 'state' in vals:
            self._check_is_agile_manager()
            new_state = vals['state']
            for sprint in self:
                if new_state == sprint.state:
                    continue
                if new_state not in SPRINT_ALLOWED_TRANSITIONS.get(sprint.state, ()):
                    raise UserError(
                        _("Invalid sprint state transition from '%s' to '%s'.")
                        % (sprint.state, new_state)
                    )
        if 'project_id' in vals and any(sprint.story_ids for sprint in self):
            raise UserError(
                _("The project of a sprint that contains stories cannot be changed.")
            )
        return super().write(vals)

    @api.depends(
        'story_ids',
        'story_ids.state',
        'story_ids.story_points',
        'state',
        'final_committed_points',
        'final_completed_points',
        'final_carry_over_points',
    )
    def _compute_sprint_metrics(self):
        """Derive committed / completed / carry-over story points from the backlog.

        For draft, planned and active sprints the figures are live sums over the
        current backlog. Once a sprint is closed or cancelled the frozen final
        values are returned, so later Story Point edits cannot rewrite history.
        """
        for sprint in self:
            if sprint.state in ('closed', 'cancelled'):
                sprint.committed_points = sprint.final_committed_points
                sprint.completed_points = sprint.final_completed_points
                sprint.carry_over_points = sprint.final_carry_over_points
                continue
            stories = sprint.story_ids
            committed = sum(s.story_points or 0 for s in stories if s.state != 'cancelled')
            completed = sum(s.story_points or 0 for s in stories if s.state == 'done')
            sprint.committed_points = int(committed)
            sprint.completed_points = int(completed)
            sprint.carry_over_points = int(committed - completed)

    @api.depends('state', 'completed_points')
    def _compute_velocity_points(self):
        """Count completed points for velocity only when the sprint is closed."""
        for sprint in self:
            sprint.velocity_points = (
                sprint.completed_points if sprint.state == 'closed' else 0
            )

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _is_agile_manager(self):
        """Return whether the current user may manage Agile sprints."""
        return self.env.su or self.env.user.has_group('amnus_agile.group_amnus_agile_manager')

    def _check_is_agile_manager(self):
        """Reject unless the current user is an AMNUS Agile Manager (or superuser)."""
        if not self._is_agile_manager():
            raise UserError(_("Only an AMNUS Agile Manager can perform this action."))

    # ------------------------------------------------------------------
    # Burndown
    # ------------------------------------------------------------------
    def _record_burndown(self, date=None, remaining=None, completed=None):
        """Append or update the burndown point for the sprint.

        Historical values are only derived from recorded sprint data; nothing is fabricated.
        """
        if self.state != 'active':
            return
        values = {
            'sprint_id': self.id,
            'date': date or fields.Date.today(),
            'remaining_points': remaining if remaining is not None else (self.committed_points - self.completed_points),
            'completed_points': completed if completed is not None else self.completed_points,
        }
        existing = self.env['amnus.agile.burndown'].sudo().search([
            ('sprint_id', '=', self.id),
            ('date', '=', values['date']),
        ], limit=1)
        if existing:
            existing.sudo().write({
                'remaining_points': values['remaining_points'],
                'completed_points': values['completed_points'],
            })
        else:
            self.env['amnus.agile.burndown'].sudo().create({
                'sprint_id': self.id,
                'date': values['date'],
                'remaining_points': values['remaining_points'],
                'completed_points': values['completed_points'],
            })

    @api.model
    def get_burndown_points(self, sprint_id):
        """Return the ordered burndown points of a sprint (chronological)."""
        return self.env['amnus.agile.burndown'].search([
            ('sprint_id', '=', sprint_id),
        ], order='date asc')

    @api.model
    def _get_sprint_velocity(self, sprint_ids=None):
        """Compute the average velocity (completed story points) of closed sprints.

        Velocity uses the frozen completion figures captured at sprint closure, so
        later Story Point edits can never rewrite past velocity.
        """
        domain = [('state', '=', 'closed')]
        if sprint_ids is not None:
            domain.append(('id', 'in', sprint_ids))
        sprints = self.env['amnus.agile.sprint'].search(domain)
        velocity = [sprint.velocity_points or 0 for sprint in sprints]
        if not velocity:
            return 0.0
        return sum(velocity) / len(velocity)

    # ------------------------------------------------------------------
    # Sprint workflow actions
    # ------------------------------------------------------------------
    def action_plan(self):
        """Move a sprint to the planned state."""
        self._check_is_agile_manager()
        for sprint in self:
            if sprint.state != 'draft':
                raise UserError(_("Only draft sprints can be planned."))
        self.sudo().write({'state': 'planned'})
        for sprint in self:
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile Sprint Planned"),
                action="state_change",
                description=_("Sprint '%(name)s' was planned.") % {'name': sprint.name},
                model_name='amnus.agile.sprint',
                record_id=sprint.id,
            )
        return True

    def action_start(self):
        """Start an active sprint and record the baseline burndown point."""
        self._check_is_agile_manager()
        for sprint in self:
            if sprint.state != 'planned':
                raise UserError(_("Only planned sprints can be started."))
        for sprint in self:
            baseline = sprint.committed_points
            for membership in sprint.membership_ids.filtered(
                lambda membership: membership.outcome == 'active'
            ):
                membership._mark_committed()
            sprint.sudo().write({
                'state': 'active',
                'baseline_points': baseline,
            })
            sprint._record_burndown(
                date=sprint.date_start,
                remaining=baseline,
                completed=0,
            )
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile Sprint Started"),
                action="state_change",
                description=_("Sprint '%(name)s' started.") % {'name': sprint.name},
                model_name='amnus.agile.sprint',
                record_id=sprint.id,
            )
        return True

    def action_close(self):
        """Close an active sprint and freeze final metrics plus the closing burndown point."""
        self._check_is_agile_manager()
        for sprint in self:
            if sprint.state != 'active':
                raise UserError(_("Only active sprints can be closed."))
        for sprint in self:
            committed = sprint.committed_points
            completed = sprint.completed_points
            carry_over = max(committed - completed, 0)
            sprint._record_burndown(
                date=sprint.date_end,
                remaining=carry_over,
                completed=completed,
            )
            sprint.sudo().write({
                'state': 'closed',
                'final_committed_points': committed,
                'final_completed_points': completed,
                'final_carry_over_points': carry_over,
            })
            for membership in sprint.membership_ids.filtered(
                lambda membership: not membership.date_removed
            ):
                story = membership.story_id
                if story.state == 'done':
                    outcome = 'completed'
                elif story.state == 'cancelled':
                    outcome = 'cancelled'
                else:
                    outcome = 'incomplete'
                membership._close(outcome)
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile Sprint Closed"),
                action="state_change",
                description=_("Sprint '%(name)s' closed.") % {'name': sprint.name},
                model_name='amnus.agile.sprint',
                record_id=sprint.id,
            )
        return True

    def action_cancel(self):
        """Cancel a sprint from a cancellable state."""
        self._check_is_agile_manager()
        for sprint in self:
            if sprint.state not in ('draft', 'planned', 'active'):
                raise UserError(_("Only draft, planned or active sprints can be cancelled."))
        for sprint in self:
            committed = sprint.committed_points
            completed = sprint.completed_points
            sprint.sudo().write({
                'state': 'cancelled',
                'final_committed_points': committed,
                'final_completed_points': completed,
                'final_carry_over_points': max(committed - completed, 0),
            })
            for membership in sprint.membership_ids.filtered(
                lambda membership: not membership.date_removed
            ):
                membership._close('cancelled')
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile Sprint Cancelled"),
                action="state_change",
                description=_("Sprint '%(name)s' was cancelled.") % {'name': sprint.name},
                model_name='amnus.agile.sprint',
                record_id=sprint.id,
            )
        return True

    def action_add_stories(self, sprint_id, story_ids):
        """Add stories to a sprint backlog."""
        self._check_is_agile_manager()
        self.ensure_one()
        sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
        if sprint.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for backlog addition."))
        if sprint.company_id != self.company_id or sprint.project_id != self.project_id:
            raise ValidationError(
                _("The sprint must belong to the same project and company as the stories.")
            )
        stories = self.env['amnus.agile.user.story'].browse(
            [story.id if hasattr(story, 'id') else story for story in story_ids]
        )
        for story in stories:
            if (
                story.project_id != sprint.project_id
                or story.company_id != sprint.company_id
            ):
                raise ValidationError(
                    _("All stories added to a sprint must belong to its project and company.")
                )
        for story in stories:
            story.sudo().write({'sprint_id': sprint.id, 'state': 'planned'})
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile Sprint Backlog Updated"),
            action="update",
            description=_("Sprint '%(sprint)s' backlog updated with %(count)d stories.") % {'sprint': sprint.name, 'count': len(stories.ids)},
            model_name='amnus.agile.sprint',
            record_id=sprint.id,
        )
        return True

    def action_carry_over(self, story_ids, target_sprint_id, reason=None):
        """Move unfinished stories to the target sprint (explicit carry-over).

        The source membership is preserved with a ``carried_over`` outcome and the
        destination sprint; a new membership row is opened in the target sprint.
        """
        self._check_is_agile_manager()
        self.ensure_one()
        target = self.env['amnus.agile.sprint'].browse(target_sprint_id)
        if target == self:
            raise UserError(_("A sprint cannot carry stories over to itself."))
        if target.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for carry-over."))
        if target.company_id != self.company_id or target.project_id != self.project_id:
            raise ValidationError(
                _("The target sprint must belong to the same project and company as the carried stories.")
            )
        stories = self.env['amnus.agile.user.story'].browse(
            [story.id if hasattr(story, 'id') else story for story in story_ids]
        )
        membership_model = self.env['amnus.agile.sprint.membership'].sudo()
        moved = []
        for story in stories:
            if story.state in ('done', 'cancelled'):
                raise UserError(_("Only unfinished user stories can be carried over."))
            if story.sprint_id != self:
                raise UserError(
                    _("Only stories currently in this sprint can be carried over.")
                )
            story.sudo().write(
                {'sprint_id': target.id, 'state': 'planned'},
                context={'amnus_agile_carry_over_replan': True},
            )
            membership = membership_model.search([
                ('sprint_id', '=', self.id),
                ('story_id', '=', story.id),
            ], limit=1)
            if membership:
                membership.sudo().write({
                    'outcome': 'carried_over',
                    'carry_over_sprint_id': target.id,
                    'reason': reason or _("Carried over to another sprint."),
                })
            moved.append(story.id)
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile Sprint Carry Over"),
            action="update",
            description=_("Sprint '%(sprint)s' carry-over moved %(count)d stories.") % {'sprint': self.name, 'count': len(moved)},
            model_name='amnus.agile.sprint',
            record_id=self.id,
        )
        return True
