# -*- coding: utf-8 -*-
"""AMNUS Agile user story: a planning artifact that may link to a task."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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

# Carry-over re-plans: an unfinished in-progress story that is moved to a later
# sprint is re-planned there (in_progress -> planned). This move is only reachable
# through the sprint carry-over action, which performs manager authorization and
# audit logging, and is gated behind this context flag.
STORY_REPLAN_SOURCE = 'in_progress'
STORY_REPLAN_TARGET = 'planned'


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
        string='Task Status',
        related='task_id.state',
        readonly=True,
        help="Execution status of the linked task. Never used to complete the story.",
    )
    task_user_ids = fields.Many2many(
        string='Task Assignees',
        related='task_id.user_ids',
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
    # Sprint membership synchronisation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Create stories and open their sprint membership row when pre-assigned."""
        stories = super().create(vals_list)
        for story in stories:
            if story.sprint_id:
                story._open_membership(story.sprint_id)
        return stories

    def _open_membership(self, sprint):
        """Open (or reopen) the membership row of this story in ``sprint``."""
        membership_model = self.env['amnus.agile.sprint.membership'].sudo()
        membership = membership_model.search([
            ('sprint_id', '=', sprint.id),
            ('story_id', '=', self.id),
        ], limit=1)
        values = {
            'date_added': fields.Datetime.now(),
            'added_by_id': self.env.user.id,
            'date_removed': False,
            'removed_by_id': False,
            'outcome': 'active',
            'carry_over_sprint_id': False,
            'reason': False,
            'committed_points': self.story_points or 0,
        }
        if membership:
            membership.write(values)
        else:
            values.update({'sprint_id': sprint.id, 'story_id': self.id})
            membership = membership_model.create(values)
        return membership

    def _close_membership(self, sprint, outcome='removed', carry_over_sprint=None, reason=None):
        """Close the open membership row of this story in ``sprint``."""
        membership = self.env['amnus.agile.sprint.membership'].sudo().search([
            ('sprint_id', '=', sprint.id),
            ('story_id', '=', self.id),
            ('date_removed', '=', False),
        ], limit=1)
        if membership:
            membership._close(
                outcome,
                carry_over_sprint=carry_over_sprint,
                reason=reason,
            )
        return membership

    # ------------------------------------------------------------------
    # ORM workflow guard: only documented state transitions are accepted
    # ------------------------------------------------------------------
    def write(self, vals, context=None):
        if ('state' in vals or 'sprint_id' in vals) and not self._is_agile_manager():
            raise UserError(
                _(
                    "Only an AMNUS Agile Manager can change story planning state "
                    "or sprint membership."
                )
            )
        if 'project_id' in vals:
            for story in self:
                if story.task_id or story.epic_id or story.sprint_id:
                    raise UserError(
                        _(
                            "The project of a user story linked to a task, epic or "
                            "sprint cannot be changed."
                        )
                    )
        if 'state' in vals:
            new_state = vals.get('state')
            for story in self:
                allowed = STORY_ALLOWED_TRANSITIONS.get(story.state, ())
                if (
                    new_state == STORY_REPLAN_TARGET
                    and story.state == STORY_REPLAN_SOURCE
                    and (context or {}).get('amnus_agile_carry_over_replan')
                ):
                    allowed = allowed + (STORY_REPLAN_TARGET,)
                if new_state not in allowed:
                    raise UserError(
                        _(
                            "Invalid user story state transition from '%s' to '%s'."
                        )
                        % (story.state, new_state)
                    )
                if new_state == 'done' and (
                    not story.acceptance_criteria or not story.acceptance_criteria.strip()
                ):
                    raise UserError(
                        _("A user story cannot be completed before acceptance criteria are set.")
                    )
        if 'story_points' in vals and not self._is_agile_manager():
            raise UserError(
                _("Only an AMNUS Agile Manager can estimate or re-estimate user stories.")
            )
        old_sprints = {}
        if 'sprint_id' in vals:
            old_sprints = {story.id: story.sprint_id for story in self}
        result = super().write(vals)
        if 'sprint_id' in vals:
            for story in self:
                old_sprint = old_sprints.get(story.id)
                if old_sprint and old_sprint != story.sprint_id:
                    story._close_membership(old_sprint, outcome='removed')
                if story.sprint_id and story.sprint_id != old_sprint:
                    story._open_membership(story.sprint_id)
        return result

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
    @api.model
    def _log_state_change(self, story_ids, old_state, new_state):
        """Append an audit event for a user story state change.

        Identity (user / company / date) is derived from the environment inside
        ``amnus.audit.log._log_event``; values are never taken from arguments.
        """
        stories = self.env['amnus.agile.user.story'].browse(story_ids)
        for story in stories:
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile User Story State Change"),
                action="state_change",
                description=_("User story '%(name)s' moved from '%(old)s' to '%(new)s'.") % {'name': story.name, 'old': old_state, 'new': new_state},
                model_name='amnus.agile.user.story',
                record_id=story.id,
            )

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_plan(self):
        """Move a backlog user story to the planned state."""
        self._check_is_agile_manager()
        for story in self:
            if story.state != 'backlog':
                raise UserError(_("Only backlog user stories can be planned."))
        self.sudo().write({'state': 'planned'})
        self._log_state_change(self.ids, 'backlog', 'planned')
        return True

    def action_start(self):
        """Start work on a planned user story."""
        self._check_is_agile_manager()
        for story in self:
            if story.state != 'planned':
                raise UserError(_("Only planned user stories can be started."))
        self.sudo().write({'state': 'in_progress'})
        self._log_state_change(self.ids, 'planned', 'in_progress')
        self._sync_sprint_burndown()
        return True

    def action_done(self):
        """Complete a user story that has acceptance criteria."""
        self._check_is_agile_manager()
        for story in self:
            if story.state != 'in_progress':
                raise UserError(_("Only in-progress user stories can be completed."))
            if not story.acceptance_criteria or not story.acceptance_criteria.strip():
                raise UserError(_("Acceptance criteria are required to complete a user story."))
        self.sudo().write({'state': 'done'})
        self._log_state_change(self.ids, 'in_progress', 'done')
        self._sync_sprint_burndown()
        return True

    def action_cancel(self):
        """Cancel a user story from a cancellable planning state."""
        self._check_is_agile_manager()
        old_states = {story.id: story.state for story in self}
        for story in self:
            if story.state not in ('backlog', 'planned', 'in_progress'):
                raise UserError(_("Only backlog, planned or in-progress user stories can be cancelled."))
        for story in self:
            self._log_state_change([story.id], old_states[story.id], 'cancelled')
        self.sudo().write({'state': 'cancelled'})
        return True

    def action_create_task(self):
        """Create the standard ``project.task`` that will execute this story.

        Execution remains owned by ``project.task``: no stage, assignee or deadline
        is copied onto the story. A task may only be linked to one story.
        """
        self._check_is_agile_manager()
        self.ensure_one()
        if self.task_id:
            raise UserError(_("This user story already has a linked task."))
        task = self.env['project.task'].create({
            'name': self.name,
            'project_id': self.project_id.id,
            'description': self.description or False,
        })
        self.sudo().write({'task_id': task.id})
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile User Story Task Linked"),
            action="create",
            description=_("Task '%(task)s' created for user story '%(story)s'.") % {
                'task': task.name,
                'story': self.name,
            },
            model_name='amnus.agile.user.story',
            record_id=self.id,
        )
        return True

    def action_add_to_sprint(self, sprint_id):
        """Assign the user story to a sprint and move it to the planned state."""
        self._check_is_agile_manager()
        self.ensure_one()
        sprint = self.env['amnus.agile.sprint'].browse(sprint_id)
        if sprint.state in ('closed', 'cancelled'):
            raise UserError(_("The target sprint is not open for backlog addition."))
        if sprint.company_id != self.company_id or sprint.project_id != self.project_id:
            raise ValidationError(
                _("The sprint must belong to the same project and company as the user story.")
            )
        self.sudo().write({'sprint_id': sprint.id, 'state': 'planned'})
        self.env['amnus.audit.log']._log_event(
            name=_("AMNUS Agile User Story Added to Sprint"),
            action="update",
            description=_("User story '%(name)s' added to sprint '%(sprint)s'.") % {'name': self.name, 'sprint': sprint.name},
            model_name='amnus.agile.user.story',
            record_id=self.id,
        )
        return True

    def action_remove_from_sprint(self):
        """Remove the user story from its sprint without deleting planning data."""
        self._check_is_agile_manager()
        self.ensure_one()
        if self.sprint_id:
            self.sudo().write({'sprint_id': False})
        return True

    # ------------------------------------------------------------------
    # Sprint burndown synchronization
    # ------------------------------------------------------------------
    def _sync_sprint_burndown(self):
        """Refresh the active sprint burndown point after a story state change."""
        for story in self:
            if story.sprint_id and story.sprint_id.state == 'active':
                sprint = self.env['amnus.agile.sprint'].browse(story.sprint_id.id)
                sprint._record_burndown()
