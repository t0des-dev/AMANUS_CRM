# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class AmnusAuditLog(models.Model):
    _name = "amnus.audit.log"
    _description = "AMNUS Audit Log"
    _order = "date desc, id desc"
    _rec_name = "name"

    name = fields.Char(string="Event", required=True, readonly=True)
    date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        readonly=True,
    )
    model_name = fields.Char(string="Model", readonly=True)
    record_id = fields.Integer(string="Record ID", readonly=True)
    action = fields.Selection(
        [
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("state_change", "State Change"),
            ("login", "Login"),
            ("export", "Export"),
            ("other", "Other"),
        ],
        string="Action",
        required=True,
        readonly=True,
    )
    description = fields.Text(string="Description", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        readonly=True,
    )

    @api.model
    def log_event(
        self,
        name,
        action,
        description="",
        model_name=None,
        record_id=None,
        user_id=None,
        company_id=None,
    ):
        """Internal API to record an audit event.

        Intended to be called by future AMNUS business addons for explicitly defined
        business events (create, update, delete, state change, login, export, other).

        The record is created with ``sudo()`` so that a business user triggering an
        auditable event can generate an audit trail entry without needing write access
        to the audit log model itself. The record is then immutable: ordinary users,
        managers and administrators cannot modify or delete audit records.

        :param name: Short event name/label.
        :param action: One of the selection values on ``action``.
        :param description: Optional free-text description.
        :param model_name: Technical name of the related model (if any).
        :param record_id: Database id of the related record (if any).
        :param user_id: User responsible for the event (defaults to current user).
        :param company_id: Company context (defaults to current company).
        :return: The created ``amnus.audit.log`` record.
        """
        vals = {
            "name": name,
            "action": action,
            "description": description or "",
            "model_name": model_name or "",
            "record_id": record_id or 0,
        }
        if user_id:
            vals["user_id"] = user_id
        if company_id:
            vals["company_id"] = company_id
        return self.sudo().create(vals)

    def write(self, vals):
        raise AccessError(_("Audit log records cannot be modified."))

    def unlink(self):
        raise AccessError(_("Audit log records cannot be deleted."))
