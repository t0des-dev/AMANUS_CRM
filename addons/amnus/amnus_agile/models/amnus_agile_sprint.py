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

# Fields frozen after sprint activation (baseline) or closure/cancellation.
# They must never be set/changed through direct ORM/RPC writes.
SPRINT_FROZEN_FIELDS = {
    'baseline_points',
    'final_committed_points',
    'final_completed_points',
    'final_carry_over_points',
}


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

    @api.constrains('capacity_points')
    def _check_capacity_points(self):
        for sprint in self:
            if sprint.capacity_points is not False and sprint.capacity_points < 0:
                raise ValidationError(_("Sprint capacity cannot be negative."))

    # ------------------------------------------------------------------
    # Controlled internal writes (bypass public guards after validation)
    # ------------------------------------------------------------------
    def _internal_write(self, vals):
        """Write through the ORM parent after server-side validation.

        This is the only path allowed to mutate protected lifecycle/frozen
        fields. Callers MUST validate authorization and workflow preconditions
        before invoking it. It is private (RPC-inaccessible) and never exposed
        through a context flag.
        """
        return models.Model.write(self.sudo(), vals)

    def _lock_for_workflow(self):
        """Acquire a row lock on sprints to serialize lifecycle/metric changes.

        Locks are acquired in ascending id order to provide a consistent lock
        acquisition order and reduce deadlock risk across multi-sprint
        operations.
        """
        if not self.ids:
            return
        self.env.cr.execute(
            "SELECT id FROM amnus_agile_sprint WHERE id IN %s FOR UPDATE",
            (tuple(sorted(self.ids)),),
        )

    @api.model
    def _lock_sprints_for_workflow(self, sprint_ids):
        """Lock arbitrary sprint ids in deterministic order."""
        ids = tuple(sorted(set(int(i) for i in sprint_ids if i)))
        if not ids:
            return
        self.env.cr.execute(
            "SELECT id FROM amnus_agile_sprint WHERE id IN %s FOR UPDATE",
            (ids,),
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Reject fabricated lifecycle states and frozen snapshots on create."""
        for vals in vals_list:
            state = vals.get('state', 'draft')
            if state != 'draft':
                raise UserError(
                    _("Sprints must be created in draft state; use the workflow actions to progress them.")
                )
            for field in SPRINT_FROZEN_FIELDS:
                if vals.get(field):
                    raise UserError(
                        _("Sprint historical/frozen fields cannot be set on create.")
                    )
        return super().create(vals_list)

    def write(self, vals):
        """Guard lifecycle transitions and protect historical figures.

        Direct ORM/RPC writes must not change sprint state or frozen snapshot
        fields. All lifecycle transitions go through the authorized action
        methods, which use the internal write path after validation.
        """
        if 'state' in vals:
            # State transitions are workflow-only; block direct writes.
            raise UserError(
                _("Sprint state cannot be changed directly. Use the sprint workflow actions.")
            )
        forbidden = SPRINT_FROZEN_FIELDS.intersection(vals)
        if forbidden:
            # Allow clearing on draft only if explicitly unset, but baseline/final
            # snapshots are never user-writable. Block any direct mutation.
            for sprint in self:
                if sprint.state in ('closed', 'cancelled'):
                    raise UserError(
                        _("Historical sprint metrics are frozen and cannot be modified.")
                    )
            raise UserError(
                _("Sprint baseline and final snapshot fields are managed by the workflow and cannot be written directly.")
            )
        if 'project_id' in vals and any(sprint.story_ids for sprint in self):
            raise UserError(
                _("The project of a sprint that contains stories cannot be changed.")
            )
        return super().write(vals)

    def unlink(self):
        """Prevent deletion of sprints that carry historical activity."""
        for sprint in self:
            if sprint.state in ('closed', 'cancelled'):
                raise UserError(
                    _("Closed or cancelled sprints cannot be deleted because they contain historical records.")
                )
            if sprint.membership_ids or sprint.burndown_point_ids:
                raise UserError(
                    _("Sprints with membership or burndown history cannot be deleted. Archive the sprint instead.")
                )
        return super().unlink()

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
    # Burndown / historical events
    # ------------------------------------------------------------------
    def _compute_burndown_figures(self):
        """Compute remaining/completed points from current (live) backlog.

        Excludes cancelled stories from remaining scope, counts done as completed.
        """
        self.ensure_one()
        stories = self.story_ids
        committed = sum(s.story_points or 0 for s in stories if s.state != 'cancelled')
        completed = sum(s.story_points or 0 for s in stories if s.state == 'done')
        remaining = max(committed - completed, 0)
        return int(remaining), int(completed)

    def _record_burndown_event(self, event_type, event_date=None, story=None,
                               points_before=None, points_after=None, force=False):
        """Record a dated burndown event as the historical source of truth.

        Events are immutable historical records created only by controlled
        server-side workflows. Timestamps/actor are derived from the
        environment and database sequence ordering, never from client input.
        ``force`` allows recording on non-active sprints for terminal workflow
        events (e.g. closure/cancellation) performed inside the controlled
        transition.

        The sprint row is locked to serialize metric/event changes and the
        burndown sequence allocation for this sprint within the current
        transaction.
        """
        self.ensure_one()
        # Serialize per-sprint history/metric updates even when caller did not
        # previously acquire a workflow lock (e.g. direct manager story edits).
        self._lock_for_workflow()
        # Concurrency fix (F-11/RISK-5): the row lock alone only *waits* the
        # competing transaction out; under REPEATABLE READ a waiter whose
        # snapshot predates the winner's commit can still allocate the same
        # event_sequence and hit SQLSTATE 23505 on the unique constraint.
        # Touching the sprint row inside the lock makes the winner visibly
        # MODIFY the row, so every waiter gets a retryable SQLSTATE 40001,
        # rolls back with a fresh snapshot and re-reads MAX(event_sequence).
        # (Documented direct SQL: lock-intent row touch only, no data change.)
        self.env.cr.execute(
            "UPDATE amnus_agile_sprint SET write_date = now() WHERE id = %s",
            (self.id,),
        )
        self.invalidate_recordset(['state', 'story_ids'])
        if not force and self.state != 'active':
            return
        remaining, completed = self._compute_burndown_figures()
        Burndown = self.env['amnus.agile.burndown'].sudo()
        # Serialize event sequence per sprint for deterministic ordering.
        # Sprint row is already locked above; MAX() cannot be combined with
        # FOR UPDATE in PostgreSQL, so rely on the sprint lock + unique
        # (sprint_id, date, event_sequence) constraint.
        self.env.cr.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) FROM amnus_agile_burndown WHERE sprint_id = %s",
            (self.id,),
        )
        next_seq = (self.env.cr.fetchone() or [0])[0] + 1
        values = {
            'sprint_id': self.id,
            'date': event_date or fields.Date.context_today(self),
            'remaining_points': remaining,
            'completed_points': completed,
            'event_type': event_type,
            'story_id': story.id if story else False,
            'points_before': points_before,
            'points_after': points_after,
            'event_sequence': next_seq,
        }
        return Burndown.create(values)

    @api.model
    def get_burndown_points(self, sprint_id):
        """Return ordered burndown events/points of a sprint (chronological)."""
        return self.env['amnus.agile.burndown'].search([
            ('sprint_id', '=', sprint_id),
        ], order='event_sequence asc, id asc')

    @api.model
    def get_burndown_series(self, sprint_id):
        """Return a continuous daily series carrying forward event-free days.

        The last known remaining/completed values are carried forward across
        dates without events. Missing rows never imply zero remaining work.
        """
        sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
        points = self.get_burndown_points(sprint_id)
        if not sprint or not points:
            return []
        by_date = {}
        for point in points:
            # last event of the day wins for that day
            by_date[point.date] = point
        dates = sorted(by_date.keys())
        start = dates[0]
        end = dates[-1]
        series = []
        current = fields.Date.from_string(start) if isinstance(start, str) else start
        last = fields.Date.from_string(end) if isinstance(end, str) else end
        last_values = None
        from datetime import timedelta
        while current <= last:
            if current in by_date:
                p = by_date[current]
                last_values = {
                    'date': current,
                    'remaining_points': p.remaining_points,
                    'completed_points': p.completed_points,
                }
            if last_values:
                series.append(dict(last_values, date=current))
            current += timedelta(days=1)
        return series

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
            sprint._lock_for_workflow()
            sprint.invalidate_recordset(['state'])
            if sprint.state != 'draft':
                raise UserError(_("Only draft sprints can be planned."))
            sprint._internal_write({'state': 'planned'})
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
            sprint._lock_for_workflow()
            sprint.invalidate_recordset(['state', 'story_ids'])
            if sprint.state != 'planned':
                raise UserError(_("Only planned sprints can be started."))
            remaining, completed = sprint._compute_burndown_figures()
            baseline = remaining + completed
            for membership in sprint.membership_ids.filtered(
                lambda membership: membership.outcome == 'active' and not membership.date_removed
            ):
                membership._mark_committed()
            sprint._internal_write({
                'state': 'active',
                'baseline_points': baseline,
            })
            # Record baseline event inside the now-active sprint (controlled).
            sprint.invalidate_recordset(['state'])
            sprint._record_burndown_event(
                'baseline',
                event_date=sprint.date_start or fields.Date.context_today(sprint),
                force=True,
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
        """Close an active sprint and freeze final metrics/history atomically."""
        self._check_is_agile_manager()
        for sprint in self:
            sprint._lock_for_workflow()
            sprint.invalidate_recordset(['state', 'story_ids'])
            if sprint.state != 'active':
                raise UserError(_("Only active sprints can be closed."))
            remaining, completed = sprint._compute_burndown_figures()
            committed = remaining + completed
            carry_over = remaining
            # Final event while still in controlled transition context.
            sprint._record_burndown_event(
                'closure',
                event_date=sprint.date_end or fields.Date.context_today(sprint),
                force=True,
            )
            sprint._internal_write({
                'state': 'closed',
                'final_committed_points': committed,
                'final_completed_points': completed,
                'final_carry_over_points': carry_over,
            })
            sprint.invalidate_recordset(['state'])
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
        """Cancel a sprint from a cancellable state and freeze metrics."""
        self._check_is_agile_manager()
        for sprint in self:
            sprint._lock_for_workflow()
            sprint.invalidate_recordset(['state', 'story_ids'])
            if sprint.state not in ('draft', 'planned', 'active'):
                raise UserError(_("Only draft, planned or active sprints can be cancelled."))
            remaining, completed = sprint._compute_burndown_figures()
            committed = remaining + completed
            if sprint.state == 'active':
                sprint._record_burndown_event(
                    'cancellation',
                    event_date=fields.Date.context_today(sprint),
                    force=True,
                )
            sprint._internal_write({
                'state': 'cancelled',
                'final_committed_points': committed,
                'final_completed_points': completed,
                'final_carry_over_points': remaining,
            })
            sprint.invalidate_recordset(['state'])
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
        """Add stories to a sprint backlog (controlled workflow)."""
        self._check_is_agile_manager()
        self.ensure_one()
        sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
        # Lock order fix (F-11/RISK-1): lock stories first (sorted), then the
        # sprint, so this workflow and the story-level workflow
        # (story -> sprint) share one global order and cannot deadlock.
        story_ids = [story.id if hasattr(story, 'id') else story for story in story_ids]
        stories = self.env['amnus.agile.user.story'].browse(story_ids)
        stories._lock_for_workflow()
        sprint._lock_for_workflow()
        sprint.invalidate_recordset(['state'])
        if sprint.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for backlog addition."))
        if sprint.company_id != self.company_id or sprint.project_id != self.project_id:
            raise ValidationError(
                _("The sprint must belong to the same project and company as the stories.")
            )
        for story in stories:
            if story.project_id != sprint.project_id or story.company_id != sprint.company_id:
                raise ValidationError(
                    _("All stories added to a sprint must belong to its project and company.")
                )
            # Delegate to story-level controlled method for validation and history.
            story._workflow_assign_to_sprint(sprint)
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile Sprint Backlog Updated"),
            action="update",
            description=_("Sprint '%(sprint)s' backlog updated with %(count)d stories.")
            % {'sprint': sprint.name, 'count': len(stories.ids)},
            model_name='amnus.agile.sprint',
            record_id=sprint.id,
        )
        return True

    def action_carry_over(self, story_ids, target_sprint_id, reason=None):
        """Move unfinished stories to the target sprint (explicit carry-over).

        Carry-over is rejected when the source sprint is closed or cancelled so
        frozen source history is never rewritten. The source open membership is
        closed as carried-over and a new membership is opened in the target.
        """
        self._check_is_agile_manager()
        self.ensure_one()
        target = self.env['amnus.agile.sprint'].browse(target_sprint_id)
        # Lock order fix (F-11/RISK-1): lock the carried stories first (sorted
        # by id), then both sprints in deterministic order. This matches the
        # global task -> story -> sprint order used by the story-level
        # workflows, so story-vs-sprint acquisition cannot deadlock.
        story_ids = [story.id if hasattr(story, 'id') else story for story in story_ids]
        stories = self.env['amnus.agile.user.story'].browse(story_ids)
        stories._lock_for_workflow()
        self._lock_sprints_for_workflow([self.id, target.id])
        self.invalidate_recordset(['state'])
        target.invalidate_recordset(['state'])
        if self.state in ('closed', 'cancelled'):
            raise UserError(
                _("Stories cannot be carried over from a closed or cancelled sprint.")
            )
        if target == self:
            raise UserError(_("A sprint cannot carry stories over to itself."))
        if target.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for carry-over."))
        if target.company_id != self.company_id or target.project_id != self.project_id:
            raise ValidationError(
                _("The target sprint must belong to the same project and company as the carried stories.")
            )
        moved = 0
        for story in stories:
            story.invalidate_recordset(['sprint_id', 'state', 'story_points', 'project_id', 'company_id'])
            if story.sprint_id != self:
                raise UserError(
                    _("Only stories currently in this sprint can be carried over.")
                )
            if story.state in ('done', 'cancelled'):
                raise UserError(_("Only unfinished user stories can be carried over."))
            if story.project_id != target.project_id or story.company_id != target.company_id:
                raise ValidationError(
                    _("The target sprint must belong to the same project and company as the carried stories.")
                )
            story._workflow_carry_over(self, target, reason=reason)
            moved += 1
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile Sprint Carry Over"),
            action="update",
            description=_("Sprint '%(sprint)s' carry-over moved %(count)d stories.")
            % {'sprint': self.name, 'count': moved},
            model_name='amnus.agile.sprint',
            record_id=self.id,
        )
        return True
