# -*- coding: utf-8 -*-
"""AMNUS Agile user story: a planning artifact that may link to a task."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

STORY_STATES = ('backlog', 'planned', 'in_progress', 'done', 'cancelled')
"""Story lifecycle states (planning artifact level)."""

STORY_ALLOWED_TRANSITIONS = {
    'backlog': ('planned', 'cancelled'),
    'planned': ('in_progress', 'cancelled'),
    'in_progress': ('done', 'cancelled'),
    'done': (),
    'cancelled': (),
}
"""Allowed user story state transitions (no backward moves, no forced completion)."""

# Fields that may be edited directly by authorized managers as planning data.
STORY_DIRECT_EDITABLE_FIELDS = {
    'name',
    'description',
    'acceptance_criteria',
    'business_value',
    'tag_ids',
    'sequence',
    'priority',
    'story_points',
    'epic_id',
    'task_id',
    'sprint_id',  # validated and handled as a controlled membership change
    'active',
}

# Workflow-owned / protected fields that cannot be set directly via ORM/RPC.
STORY_PROTECTED_FIELDS = {'state'}


class AmnusAgileUserStory(models.Model):
    """AMNUS Agile user story: a planning artifact that may link to a task.

    The standard ``project.task`` remains the single execution model. A user story
    carries planning metadata (acceptance criteria, story points, epic, sprint) and
    points to an optional task without duplicating task fields.

    Story completion is defined here (acceptance criteria must be satisfied) and is
    intentionally *not* coupled to ``amnus.project.deliverable`` acceptance: contractual
    deliverable acceptance and Agile story completion are distinct concepts.
    """

    _name = 'amnus.agile.user.story'
    _description = 'AMNUS Agile User Story'
    _check_company_auto = True
    _order = 'project_id, epic_id, sequence, id'

    name = fields.Char(string='Story Title', required=True)
    description = fields.Text(string='Description')
    acceptance_criteria = fields.Text(string='Acceptance Criteria')
    business_value = fields.Text(string='Business Value')
    tag_ids = fields.Many2many(
        'amnus.tag',
        relation='amnus_agile_story_tag_rel',
        column1='story_id',
        column2='tag_id',
        string='Tags',
        check_company=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        ondelete='cascade',
        index=True,
    )
    epic_id = fields.Many2one(
        'amnus.agile.epic',
        string='Epic',
        ondelete='set null',
        index=True,
    )
    task_id = fields.Many2one(
        'project.task',
        string='Linked Task',
        ondelete='set null',
        index=True,
        copy=False,
    )
    task_state = fields.Selection(
        selection=lambda self: self.env['project.task']._fields['state'].selection,
        string='Task Status',
        compute='_compute_task_info',
        compute_sudo=False,
        readonly=True,
        help="Execution status of the linked task. Never used to complete the story.",
    )
    task_user_ids = fields.Many2many(
        'res.users',
        string='Task Assignees',
        compute='_compute_task_info',
        compute_sudo=False,
        readonly=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    priority = fields.Selection(
        [
            ('0', 'Low priority'),
            ('1', 'Medium priority'),
            ('2', 'High priority'),
            ('3', 'Urgent'),
        ],
        string='Priority',
        default='0',
        index=True,
    )
    story_points = fields.Integer(string='Story Points')
    state = fields.Selection(
        [
            ('backlog', 'Backlog'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='State',
        default='backlog',
        required=True,
        index=True,
        copy=False,
    )
    sprint_id = fields.Many2one(
        'amnus.agile.sprint',
        string='Sprint',
        ondelete='set null',
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
    active = fields.Boolean(string='Active', default=True)

    _task_id_unique = models.Constraint(
        'unique (task_id)',
        'A project task can only be linked to one user story.',
    )

    # ------------------------------------------------------------------
    # Computed / access-safe task info (F-02)
    # ------------------------------------------------------------------
    @api.depends('task_id')
    def _compute_task_info(self):
        """Expose linked task state/assignees without sudo privilege escalation.

        If the current user cannot read the linked task, inaccessible values are
        omitted instead of disclosed.
        """
        for story in self:
            task = story.task_id
            if not task:
                story.task_state = False
                story.task_user_ids = self.env['res.users']
                continue
            try:
                task.check_access('read')
                # Read with current user's rights only.
                task_visible = task.with_env(self.env)
                story.task_state = task_visible.state
                story.task_user_ids = task_visible.user_ids
            except AccessError:
                story.task_state = False
                story.task_user_ids = self.env['res.users']

    # ------------------------------------------------------------------
    # ORM constraints
    # ------------------------------------------------------------------
    @api.constrains('task_id')
    def _check_single_task_story(self):
        """Enforce the one-to-one story/task relationship at the ORM level."""
        for story in self:
            if not story.task_id:
                continue
            duplicates = self.sudo().search_count([
                ('task_id', '=', story.task_id.id),
                ('id', '!=', story.id),
            ])
            if duplicates:
                raise ValidationError(
                    _("A project task can only be linked to one user story.")
                )

    @api.constrains('task_id')
    def _check_task_project(self):
        for story in self:
            if story.task_id and story.task_id.project_id != story.project_id:
                raise ValidationError(
                    _("The linked task must belong to the same project as the user story.")
                )

    @api.constrains('epic_id')
    def _check_epic_project(self):
        for story in self:
            if story.epic_id and story.epic_id.project_id != story.project_id:
                raise ValidationError(
                    _("The epic must belong to the same project as the user story.")
                )

    @api.constrains('sprint_id')
    def _check_sprint_project(self):
        for story in self:
            if story.sprint_id and (
                story.sprint_id.project_id != story.project_id
                or story.sprint_id.company_id != story.company_id
            ):
                raise ValidationError(
                    _("The sprint must belong to the same project and company as the user story.")
                )

    @api.constrains('story_points')
    def _check_story_points(self):
        for story in self:
            if story.story_points and story.story_points not in (1, 2, 3, 5, 8, 13, 21):
                raise ValidationError(
                    _("Story points must be one of 1, 2, 3, 5, 8, 13, 21.")
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _internal_write(self, vals):
        """Internal write bypassing direct-write guards after validation."""
        return models.Model.write(self.sudo(), vals)

    def _lock_for_workflow(self):
        """Lock story rows to serialize sprint/membership/task-link changes."""
        if not self.ids:
            return
        self.env.cr.execute(
            "SELECT id FROM amnus_agile_user_story WHERE id IN %s FOR UPDATE",
            (tuple(sorted(self.ids)),),
        )

    def _is_sprint_open(self, sprint):
        return bool(sprint) and sprint.state not in ('closed', 'cancelled')

    def _validate_sprint_assignment(self, sprint):
        """Ensure a story may be assigned to the given sprint."""
        self.ensure_one()
        if not sprint:
            return
        if sprint.state in ('closed', 'cancelled'):
            raise UserError(
                _("User stories cannot be assigned to a closed or cancelled sprint.")
            )
        if sprint.project_id != self.project_id or sprint.company_id != self.company_id:
            raise ValidationError(
                _("The sprint must belong to the same project and company as the user story.")
            )

    # ------------------------------------------------------------------
    # Sprint membership synchronisation
    # ------------------------------------------------------------------
    def _open_membership(self, sprint, committed_points=None):
        """Open a membership row for this story in ``sprint``.

        Closed/removed rows are never rewritten (append-only history). If an
        open row already exists it is refreshed; if only closed rows exist, a
        new row is not created because of the (sprint, story) uniqueness
        constraint — re-entry into the same sprint after removal is rejected to
        preserve history integrity.
        """
        self.ensure_one()
        # Serialize membership changes per story and sprint.
        self._lock_for_workflow()
        if sprint:
            sprint._lock_for_workflow()
            sprint.invalidate_recordset(['state'])
            if sprint.state in ('closed', 'cancelled'):
                raise UserError(
                    _("User stories cannot be assigned to a closed or cancelled sprint.")
                )
        membership_model = self.env['amnus.agile.sprint.membership'].sudo()
        existing = membership_model.search([
            ('sprint_id', '=', sprint.id),
            ('story_id', '=', self.id),
        ], order='id desc', limit=1)
        points = self.story_points or 0 if committed_points is None else committed_points
        if existing:
            if existing.outcome == 'active' and not existing.date_removed:
                # Refresh an open row (e.g. initial commitment capture).
                existing.write({
                    'committed_points': points,
                })
                return existing
            # Historical closed row exists for same sprint/story: do not rewrite.
            raise UserError(
                _("This user story already has historical membership in this sprint and cannot be re-added.")
            )
        # Defensive check before insert (DB partial unique index enforces globally).
        open_elsewhere = membership_model.search_count([
            ('story_id', '=', self.id),
            ('outcome', '=', 'active'),
            ('date_removed', '=', False),
            ('sprint_id', '!=', sprint.id),
        ])
        if open_elsewhere:
            raise UserError(
                _("A user story cannot belong to two sprints at the same time.")
            )
        return membership_model.create({
            'sprint_id': sprint.id,
            'story_id': self.id,
            'date_added': fields.Datetime.now(),
            'added_by_id': self.env.user.id,
            'outcome': 'active',
            'committed_points': points,
        })

    def _close_membership(self, sprint, outcome='removed', carry_over_sprint=None, reason=None):
        """Close the open membership row of this story in ``sprint``."""
        self.ensure_one()
        membership = self.env['amnus.agile.sprint.membership'].sudo().search([
            ('sprint_id', '=', sprint.id),
            ('story_id', '=', self.id),
            ('date_removed', '=', False),
            ('outcome', '=', 'active'),
        ], limit=1)
        if membership:
            membership._close(
                outcome,
                carry_over_sprint=carry_over_sprint,
                reason=reason,
            )
        return membership

    # ------------------------------------------------------------------
    # Create / write / unlink
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Create stories with workflow-safe defaults and validated relations."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            state = vals.get('state', 'backlog')
            if state == 'done':
                if not (vals.get('acceptance_criteria') or '').strip():
                    raise UserError(
                        _("A user story cannot be created as done without acceptance criteria.")
                    )
                # Direct creation of done stories bypasses workflow history; disallow.
                raise UserError(
                    _("User stories cannot be created directly in a done state. Complete them through the workflow.")
                )
            if state not in ('backlog', 'planned'):
                raise UserError(
                    _("User stories must be created in backlog or planned state.")
                )
            prepared.append(vals)

        # Validate sprint targets before create.
        Sprint = self.env['amnus.agile.sprint']
        Project = self.env['project.project']
        sprint_ids = [vals['sprint_id'] for vals in prepared if vals.get('sprint_id')]
        if sprint_ids:
            Sprint._lock_sprints_for_workflow(sprint_ids)
        for vals in prepared:
            if vals.get('sprint_id'):
                sprint = Sprint.browse(vals['sprint_id'])
                if not sprint.exists():
                    raise ValidationError(_("The selected sprint does not exist."))
                sprint.invalidate_recordset(['state', 'project_id', 'company_id'])
                if sprint.state in ('closed', 'cancelled'):
                    raise UserError(
                        _("User stories cannot be assigned to a closed or cancelled sprint.")
                    )
                project_id = vals.get('project_id')
                if project_id:
                    project = Project.browse(project_id)
                    if sprint.project_id != project or sprint.company_id != project.company_id:
                        raise ValidationError(
                            _("The sprint must belong to the same project and company as the user story.")
                        )

        stories = super().create(prepared)
        for story in stories:
            if story.sprint_id:
                # Lock created story before opening membership/history updates.
                story._lock_for_workflow()
                story._open_membership(story.sprint_id)
                if story.sprint_id.state == 'active':
                    story.sprint_id._record_burndown_event(
                        'scope_add', story=story, points_after=story.story_points or 0
                    )
        return stories

    def write(self, vals):
        """Enforce workflow, membership, history and relational integrity."""
        vals = dict(vals)
        # No unknown protected workflow injection via direct fields except handled ones.
        if vals.get('state') and vals['state'] != vals.get('_internal_state'):
            # Direct state writes are not allowed; workflow methods use _workflow_transition.
            # (No special key accepted from callers.)
            pass
        direct_state = vals.pop('state', None)

        # Authorization checks
        if direct_state is not None and not self._is_agile_manager():
            raise UserError(
                _("Only an AMNUS Agile Manager can change story planning state or sprint membership.")
            )
        if 'sprint_id' in vals and not self._is_agile_manager():
            raise UserError(
                _("Only an AMNUS Agile Manager can change story planning state or sprint membership.")
            )
        if 'story_points' in vals and not self._is_agile_manager():
            raise UserError(
                _("Only an AMNUS Agile Manager can estimate or re-estimate user stories.")
            )

        # Direct state change: reject (must use workflow). Allow only when equal.
        if direct_state is not None:
            for story in self:
                if direct_state != story.state:
                    raise UserError(
                        _("Story state cannot be changed directly. Use the story workflow actions.")
                    )
            # same-state no-op, drop key
            direct_state = None

        if 'project_id' in vals:
            for story in self:
                if story.task_id or story.epic_id or story.sprint_id:
                    raise UserError(
                        _("The project of a user story linked to a task, epic or sprint cannot be changed.")
                    )

        # Serialize affected stories and sprints for sprint/metric-sensitive edits.
        needs_sprint_lock = 'sprint_id' in vals or 'story_points' in vals
        old_sprints = {}
        target_sprint = self.env['amnus.agile.sprint']
        if needs_sprint_lock and self.ids:
            self._lock_for_workflow()
            self.invalidate_recordset(['sprint_id', 'story_points', 'project_id', 'company_id', 'state'])
            sprint_ids = []
            for story in self:
                if story.sprint_id:
                    sprint_ids.append(story.sprint_id.id)
            if 'sprint_id' in vals:
                target_sprint = self.env['amnus.agile.sprint'].browse(vals['sprint_id']) if vals['sprint_id'] else self.env['amnus.agile.sprint']
                if target_sprint:
                    sprint_ids.append(target_sprint.id)
            if sprint_ids:
                self.env['amnus.agile.sprint']._lock_sprints_for_workflow(sprint_ids)
                self.env['amnus.agile.sprint'].browse(list(set(sprint_ids))).invalidate_recordset(['state', 'project_id', 'company_id'])
                self.invalidate_recordset(['sprint_id', 'story_points', 'project_id', 'company_id', 'state'])

        # Validate sprint target before applying.
        if 'sprint_id' in vals:
            for story in self:
                old_sprints[story.id] = story.sprint_id
                if target_sprint:
                    story._validate_sprint_assignment(target_sprint)
        elif needs_sprint_lock:
            # Refresh old sprint mapping after lock for point-only updates.
            for story in self:
                old_sprints[story.id] = story.sprint_id

        # Capture old points for burndown events.
        old_points = {story.id: (story.story_points or 0) for story in self} if 'story_points' in vals else {}

        result = super().write(vals)

        # Post-write side effects for sprint membership changes.
        if 'sprint_id' in vals:
            for story in self:
                old_sprint = old_sprints.get(story.id)
                new_sprint = story.sprint_id
                if old_sprint == new_sprint:
                    continue
                if old_sprint:
                    # Close open membership in old sprint as removed (if open).
                    story._close_membership(old_sprint, outcome='removed')
                    if old_sprint.state == 'active':
                        old_sprint._record_burndown_event(
                            'scope_remove', story=story,
                            points_before=old_points.get(story.id, story.story_points or 0),
                        )
                if new_sprint:
                    story._open_membership(new_sprint)
                    if new_sprint.state == 'active':
                        new_sprint._record_burndown_event(
                            'scope_add', story=story,
                            points_after=story.story_points or 0,
                        )

        # Story point re-estimation event (if points changed and story is in an active sprint).
        if 'story_points' in vals:
            for story in self:
                old = old_points.get(story.id, 0)
                new = story.story_points or 0
                if old != new and story.sprint_id and story.sprint_id.state == 'active':
                    story.sprint_id._record_burndown_event(
                        'reestimate', story=story, points_before=old, points_after=new,
                    )

        return result

    def unlink(self):
        """Protect historical sprint integrity on story deletion."""
        for story in self:
            if story.sprint_id and story.sprint_id.state in ('closed', 'cancelled'):
                raise UserError(
                    _("Stories belonging to a closed or cancelled sprint cannot be deleted.")
                )
            # If story has membership history, prevent deletion to preserve append-only records.
            memberships = self.env['amnus.agile.sprint.membership'].sudo().search_count([
                ('story_id', '=', story.id),
            ])
            if memberships:
                raise UserError(
                    _("Stories with sprint membership history cannot be deleted. Archive the story instead.")
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------
    def _is_agile_manager(self):
        """Return whether the current user may manage Agile planning."""
        return self.env.su or self.env.user.has_group('amnus_agile.group_amnus_agile_manager')

    def _check_is_agile_manager(self):
        """Reject unless the current user is an AMNUS Agile Manager (or superuser)."""
        if not self._is_agile_manager():
            raise UserError(_("Only an AMNUS Agile Manager can perform this action."))

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------
    def _log_state_change(self, old_state, new_state):
        """Append an audit event for a user story state change."""
        for story in self:
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile User Story State Change"),
                action="state_change",
                description=_("User story '%(name)s' moved from '%(old)s' to '%(new)s'.")
                % {'name': story.name, 'old': old_state, 'new': new_state},
                model_name='amnus.agile.user.story',
                record_id=story.id,
            )

    # ------------------------------------------------------------------
    # Controlled workflow transitions
    # ------------------------------------------------------------------
    def _workflow_transition(self, target_state):
        """Perform an authorized, validated state transition with side effects."""
        self._check_is_agile_manager()
        for story in self:
            current = story.state
            if current == target_state:
                continue
            allowed = STORY_ALLOWED_TRANSITIONS.get(current, ())
            if target_state not in allowed:
                raise UserError(
                    _("Invalid user story state transition from '%s' to '%s'.")
                    % (current, target_state)
                )
            if target_state == 'done':
                if not story.acceptance_criteria or not story.acceptance_criteria.strip():
                    raise UserError(
                        _("A user story cannot be completed before acceptance criteria are set.")
                    )
            # Apply transition
            story._internal_write({'state': target_state})
            story._log_state_change(current, target_state)
            # Burndown/history side effects
            sprint = story.sprint_id
            if sprint and sprint.state == 'active':
                if target_state == 'done':
                    sprint._record_burndown_event(
                        'completion', story=story,
                        points_before=story.story_points or 0,
                        points_after=story.story_points or 0,
                    )
                elif target_state == 'cancelled':
                    sprint._record_burndown_event(
                        'cancellation', story=story,
                        points_before=story.story_points or 0,
                    )
        return True

    def _workflow_assign_to_sprint(self, sprint):
        """Controlled assignment of story to an open sprint (manager-validated)."""
        self.ensure_one()
        self._check_is_agile_manager()
        # Serialize story and affected sprints; lock in deterministic sprint order.
        self._lock_for_workflow()
        self.invalidate_recordset(['sprint_id', 'state', 'story_points', 'project_id', 'company_id'])
        old_sprint = self.sprint_id
        sprint_ids = [s.id for s in [old_sprint, sprint] if s]
        if sprint_ids:
            self.env['amnus.agile.sprint']._lock_sprints_for_workflow(sprint_ids)
            self.env['amnus.agile.sprint'].browse(list(set(sprint_ids))).invalidate_recordset(['state', 'project_id', 'company_id'])
            self.invalidate_recordset(['sprint_id', 'state', 'story_points', 'project_id', 'company_id'])
            old_sprint = self.sprint_id
        self._validate_sprint_assignment(sprint)
        if old_sprint == sprint:
            # Idempotent: ensure planned state if backlog? keep current if allowed.
            if self.state == 'backlog':
                self._workflow_transition('planned')
            return True
        # Close old open membership
        if old_sprint:
            self._close_membership(old_sprint, outcome='removed')
            if old_sprint.state == 'active':
                old_sprint._record_burndown_event(
                    'scope_remove', story=self, points_before=self.story_points or 0,
                )
        # Move to planned if in backlog (allowed). If in_progress, cannot assign directly
        # except through carry-over; treat in_progress as invalid here for safety.
        if self.state == 'backlog':
            self._internal_write({'sprint_id': sprint.id, 'state': 'planned'})
            self._log_state_change('backlog', 'planned')
        elif self.state == 'planned':
            self._internal_write({'sprint_id': sprint.id})
        else:
            raise UserError(
                _("Only backlog or planned user stories can be added to a sprint.")
            )
        self.invalidate_recordset(['sprint_id', 'state'])
        self._open_membership(sprint)
        if sprint.state == 'active':
            sprint._record_burndown_event(
                'scope_add', story=self, points_after=self.story_points or 0,
            )
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile User Story Added to Sprint"),
            action="update",
            description=_("User story '%(name)s' added to sprint '%(sprint)s'.")
            % {'name': self.name, 'sprint': sprint.name},
            model_name='amnus.agile.user.story',
            record_id=self.id,
        )
        return True

    def _workflow_carry_over(self, source_sprint, target_sprint, reason=None):
        """Controlled carry-over preserving source history (F-07).

        Source sprint must be open; target must be open. The source open
        membership is closed as carried-over. Source closed memberships are never
        rewritten.
        """
        self.ensure_one()
        self._check_is_agile_manager()
        self._lock_for_workflow()
        self.invalidate_recordset(['sprint_id', 'state', 'story_points', 'project_id', 'company_id'])
        # Sprints should already be locked by caller in deterministic order.
        source_sprint.invalidate_recordset(['state'])
        target_sprint.invalidate_recordset(['state'])
        if source_sprint.state in ('closed', 'cancelled'):
            raise UserError(
                _("Stories cannot be carried over from a closed or cancelled sprint.")
            )
        if target_sprint.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for carry-over."))
        if self.sprint_id != source_sprint:
            raise UserError(_("Only stories currently in this sprint can be carried over."))
        if self.state in ('done', 'cancelled'):
            raise UserError(_("Only unfinished user stories can be carried over."))
        self._validate_sprint_assignment(target_sprint)

        points = self.story_points or 0
        # Close source open membership as carried_over (never rewrite closed history).
        open_membership = self.env['amnus.agile.sprint.membership'].sudo().search([
            ('sprint_id', '=', source_sprint.id),
            ('story_id', '=', self.id),
            ('date_removed', '=', False),
            ('outcome', '=', 'active'),
        ], limit=1)
        if open_membership:
            open_membership._close(
                'carried_over',
                carry_over_sprint=target_sprint,
                reason=reason or _("Carried over to another sprint."),
            )

        # Move story to target sprint, replanning in-progress work.
        target_state = 'planned'
        old_state = self.state
        self._internal_write({'sprint_id': target_sprint.id, 'state': target_state})
        self.invalidate_recordset(['sprint_id', 'state'])
        # Record source removal/carry-out after story leaves source backlog.
        if source_sprint.state == 'active':
            source_sprint.invalidate_recordset(['story_ids'])
            source_sprint._record_burndown_event(
                'carry_over_out', story=self, points_before=points,
            )
        self._open_membership(target_sprint)
        if old_state != target_state:
            self._log_state_change(old_state, target_state)
        if target_sprint.state == 'active':
            target_sprint.invalidate_recordset(['story_ids'])
            target_sprint._record_burndown_event(
                'carry_over_in', story=self, points_after=points,
            )
        return True

    # ------------------------------------------------------------------
    # Workflow actions (public, authorized)
    # ------------------------------------------------------------------
    def action_plan(self):
        """Move a backlog user story to the planned state."""
        for story in self:
            if story.state != 'backlog':
                raise UserError(_("Only backlog user stories can be planned."))
        return self._workflow_transition('planned')

    def action_start(self):
        """Start work on a planned user story."""
        for story in self:
            if story.state != 'planned':
                raise UserError(_("Only planned user stories can be started."))
        return self._workflow_transition('in_progress')

    def action_done(self):
        """Complete a user story that has acceptance criteria."""
        for story in self:
            if story.state != 'in_progress':
                raise UserError(_("Only in-progress user stories can be completed."))
            if not story.acceptance_criteria or not story.acceptance_criteria.strip():
                raise UserError(_("Acceptance criteria are required to complete a user story."))
        return self._workflow_transition('done')

    def action_cancel(self):
        """Cancel a user story from a cancellable planning state."""
        for story in self:
            if story.state not in ('backlog', 'planned', 'in_progress'):
                raise UserError(_("Only backlog, planned or in-progress user stories can be cancelled."))
        return self._workflow_transition('cancelled')

    def action_create_task(self):
        """Create the standard ``project.task`` that will execute this story."""
        self._check_is_agile_manager()
        self.ensure_one()
        self._lock_for_workflow()
        self.invalidate_recordset(['task_id', 'project_id'])
        if self.task_id:
            raise UserError(_("This user story already has a linked task."))
        task = self.env['project.task'].create({
            'name': self.name,
            'project_id': self.project_id.id,
            'description': self.description or False,
        })
        # Lock task to serialize with concurrent task moves (F-02/race 5).
        self.env.cr.execute(
            "SELECT id FROM project_task WHERE id = %s FOR UPDATE",
            (task.id,),
        )
        self._internal_write({'task_id': task.id})
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile User Story Task Linked"),
            action="create",
            description=_("Task '%(task)s' created for user story '%(story)s'.")
            % {'task': task.name, 'story': self.name},
            model_name='amnus.agile.user.story',
            record_id=self.id,
        )
        return True

    def action_add_to_sprint(self, sprint_id):
        """Assign the user story to a sprint through the controlled workflow."""
        self.ensure_one()
        sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
        return self._workflow_assign_to_sprint(sprint)

    def action_remove_from_sprint(self):
        """Remove the user story from its sprint without deleting planning data."""
        self._check_is_agile_manager()
        self.ensure_one()
        self._lock_for_workflow()
        self.invalidate_recordset(['sprint_id', 'story_points'])
        if not self.sprint_id:
            return True
        sprint = self.sprint_id
        sprint._lock_for_workflow()
        sprint.invalidate_recordset(['state'])
        self._close_membership(sprint, outcome='removed')
        if sprint.state == 'active':
            sprint._record_burndown_event(
                'scope_remove', story=self, points_before=self.story_points or 0,
            )
        self._internal_write({'sprint_id': False})
        return True

    def _sync_sprint_burndown(self):
        """Compatibility helper: record a generic event for active sprint if needed."""
        for story in self:
            if story.sprint_id and story.sprint_id.state == 'active':
                story.sprint_id._record_burndown_event('update', story=story)
