# -*- coding: utf-8 -*-
"""AMNUS Agile epic: a large body of work grouping user stories."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AmnusAgileEpic(models.Model):
    """AMNUS Agile epic: a large body of work grouping user stories.

    An epic belongs to one project and one company and groups user stories of that
    same project. Its progress is derived from the completion of its linked stories
    only; task-level execution data is not duplicated here.
    """

    _name = 'amnus.agile.epic'
    _description = 'AMNUS Agile Epic'
    _order = 'project_id, sequence, id'

    name = fields.Char(string='Epic Name', required=True)
    description = fields.Text(string='Description')
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
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection(
        [
            ('open', 'Open'),
            ('done', 'Done'),
        ],
        string='State',
        default='open',
        required=True,
        index=True,
        copy=False,
    )
    story_ids = fields.One2many(
        'amnus.agile.user.story',
        'epic_id',
        string='User Stories',
    )
    active = fields.Boolean(string='Active', default=True)
    story_count = fields.Integer(
        string='Stories',
        compute='_compute_epic_progress',
        readonly=True,
    )
    completed_story_count = fields.Integer(
        string='Completed Stories',
        compute='_compute_epic_progress',
        readonly=True,
    )
    progress = fields.Float(
        string='Progress (%)',
        compute='_compute_epic_progress',
        readonly=True,
        digits=(5, 2),
    )

    @api.depends('story_ids', 'story_ids.state')
    def _compute_epic_progress(self):
        """Compute epic progress from linked story completion (not task counts)."""
        for epic in self:
            stories = epic.story_ids
            epic.story_count = len(stories)
            epic.completed_story_count = len(
                [s for s in stories if s.state == 'done']
            )
            epic.progress = (
                100.0 * len([s for s in stories if s.state == 'done']) / len(stories)
                if stories
                else 0.0
            )

    # ------------------------------------------------------------------
    # Guards / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        """Prevent invalid project moves and direct state bypass."""
        if 'project_id' in vals:
            for epic in self:
                if epic.story_ids:
                    raise UserError(
                        _("The project of an epic that contains stories cannot be changed.")
                    )
        if 'state' in vals:
            new_state = vals['state']
            for epic in self:
                if new_state == epic.state:
                    continue
                # Only open -> done allowed, and only via controlled workflow.
                raise UserError(
                    _("Epic state cannot be changed directly. Use the epic workflow actions.")
                )
        return super().write(vals)

    def unlink(self):
        for epic in self:
            if epic.story_ids:
                raise UserError(
                    _("Epics that contain user stories cannot be deleted. Archive the epic instead.")
                )
        return super().unlink()

    def _is_agile_manager(self):
        """Return whether the current user may manage Agile epics."""
        return self.env.su or self.env.user.has_group('amnus_agile.group_amnus_agile_manager')

    def _check_is_agile_manager(self):
        """Reject unless the current user is an AMNUS Agile Manager (or superuser)."""
        if not self._is_agile_manager():
            raise UserError(_("Only an AMNUS Agile Manager can perform this action."))

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_done(self):
        """Mark the epic as done."""
        self._check_is_agile_manager()
        for epic in self:
            if epic.state != 'open':
                raise UserError(_("Only open epics can be marked done."))
            super(AmnusAgileEpic, epic.sudo()).write({'state': 'done'})
            self.env['amnus.audit.log']._log_event(
                name=_("AMNUS Agile Epic Completed"),
                action="state_change",
                description=_("Epic '%(name)s' was marked done.") % {'name': epic.name},
                model_name='amnus.agile.epic',
                record_id=epic.id,
            )
        return True
