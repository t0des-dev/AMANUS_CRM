# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AmnusTag(models.Model):
    _name = "amnus.tag"
    _description = "AMNUS Tag"
    _order = "category, name"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    color = fields.Integer(string="Color Index")
    active = fields.Boolean(string="Active", default=True)
    category = fields.Selection(
        [
            ("general", "General"),
            ("project", "Project"),
            ("analysis", "Analysis"),
            ("agile", "Agile"),
            ("development", "Development"),
            ("qa", "Quality Assurance"),
            ("support", "Support"),
        ],
        string="Category",
        default="general",
        required=True,
    )
    description = fields.Text(string="Description", translate=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            "amnus_tag_name_category_company_uniq",
            "UNIQUE(name, category, company_id)",
            _("A tag with the same name and category already exists for this company."),
        ),
    ]

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_("The tag name cannot be empty."))
