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
    def _log_event(
        self,
        name,
        action,
        description="",
        model_name=None,
        record_id=None,
    ):
        """Internal API to record an audit event.

        Intended to be called by AMNUS business addons for explicitly defined
        business events (create, update, delete, state change, login, export,
        other).

        The leading underscore makes this method non-callable through Odoo's
        XML-RPC / JSON-RPC interface (``execute_kw`` rejects underscore-prefixed
        methods), so ordinary users cannot trigger arbitrary audit records
        remotely.

        The audit record is created with ``sudo()`` because the ACL on
        ``amnus.audit.log`` denies create/write/unlink to every AMNUS group:
        business code triggering an auditable event must be able to write the
        trail entry without granting users direct write access to the log. This
        ``sudo()`` is scoped to this single, controlled create call and the
        sensitive fields (user, company, date) are derived from the
        authenticated environment, never from caller arguments.

        Caller-supplied ``user_id`` / ``company_id`` are intentionally NOT
        accepted: identity is always derived from ``self.env.user`` and
        ``self.env.company`` so it cannot be forged.

        :param name: Short event name/label.
        :param action: One of the selection values on ``action``.
        :param description: Optional free-text description.
        :param model_name: Technical name of the related model (if any).
        :param record_id: Database id of the related record (if any).
        :return: The created ``amnus.audit.log`` record.
        """
        vals = {
            "name": name,
            "action": action,
            "description": description or "",
            "model_name": model_name or "",
            "record_id": record_id or 0,
            # Identity derived from the authenticated environment (never forged).
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
        }
        return self.sudo().create(vals)

    def write(self, vals):
        raise AccessError(_("Audit log records cannot be modified."))

    def unlink(self):
        raise AccessError(_("Audit log records cannot be deleted."))
