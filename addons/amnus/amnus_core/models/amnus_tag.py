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
        help="Leave empty for a global tag shared across all companies.",
    )

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_("The tag name cannot be empty."))

    @api.constrains("name", "category", "company_id")
    def _check_duplicate_tag(self):
        """Prevent duplicate tags, treating a missing company (global tag) as a
        single shared scope.

        PostgreSQL UNIQUE considers NULL distinct, so it does not block two
        global tags (company_id IS NULL) sharing the same name+category. This
        constraint closes that gap while preserving company isolation:

        * Global tag (company_id empty): name+category must be unique among all
          global tags.
        * Company-specific tag: name+category must be unique within that company.
        * Same name in different categories: allowed.
        * Same name in different companies: allowed (company isolation).
        """
        for record in self:
            if not record.name or not record.name.strip():
                continue
            domain = [
                ("name", "=", record.name.strip()),
                ("category", "=", record.category),
                ("id", "!=", record.id),
            ]
            if record.company_id:
                # Company-specific tag: block if another tag with same
                # name+category exists for the same company, OR a global tag
                # already claims that name+category (global scope is shared).
                domain.extend(
                    ["|", ("company_id", "=", record.company_id.id), ("company_id", "=", False)]
                )
            else:
                # Global tag: block if any global tag (company_id empty) already
                # uses this name+category.
                domain.append(("company_id", "=", False))
            duplicates = self.search(domain)
            if duplicates:
                raise ValidationError(
                    _(
                        "A tag with the name '%(name)s' and category '%(category)s' "
                        "already exists in this scope."
                    )
                    % {
                        "name": record.name,
                        "category": dict(record._fields["category"].selection).get(
                            record.category
                        ),
                    }
                )
