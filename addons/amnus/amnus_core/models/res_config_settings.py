# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    amnus_enabled = fields.Boolean(string="AMNUS Enabled", default=True)
    amnus_audit_logging = fields.Boolean(string="Audit Logging Enabled", default=True)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "amnus_core.enabled", str(bool(self.amnus_enabled))
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "amnus_core.audit_logging", str(bool(self.amnus_audit_logging))
        )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env["ir.config_parameter"].sudo()
        res["amnus_enabled"] = ICPSudo.get_param("amnus_core.enabled", default="True") == "True"
        res["amnus_audit_logging"] = ICPSudo.get_param("amnus_core.audit_logging", default="True") == "True"
        return res
