# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import ValidationError, AccessError


@tagged("standard", "amnus_core", "at_install", "-post_install")
class TestAmnusTag(common.TransactionCase):
    """Tests for the AMNUS Tag shared model."""

    def setUp(self):
        super().setUp()
        self.tag_model = self.env["amnus.tag"]

    def _make_company(self, name):
        return self.env["res.company"].create({"name": name})

    # --- Creation / required fields -------------------------------------

    def test_create_tag(self):
        tag = self.tag_model.create({"name": "Test Tag", "category": "project"})
        self.assertTrue(tag.id)
        self.assertEqual(tag.name, "Test Tag")
        self.assertEqual(tag.category, "project")
        self.assertTrue(tag.active)

    def test_required_name(self):
        # Odoo 19 enforces required=True at the SQL level (NOT NULL).
        # Creating a tag without a name raises a database-level error.
        # We verify the field is required by checking the model definition.
        self.assertTrue(self.tag_model._fields["name"].required)

    def test_empty_name_rejected(self):
        with self.assertRaises(ValidationError):
            self.tag_model.create({"name": "   ", "category": "project"})

    def test_archive_tag(self):
        tag = self.tag_model.create({"name": "Archive Me"})
        tag.action_archive()
        self.assertFalse(tag.active)

    def test_search_behavior(self):
        self.tag_model.create({"name": "Searchable Tag", "category": "analysis"})
        tags = self.tag_model.search([("name", "ilike", "Searchable")])
        self.assertEqual(len(tags), 1)

    # --- Uniqueness (global vs company-scoped) --------------------------

    def test_duplicate_global_tag_blocked(self):
        """Two global tags (no company) with same name+category are duplicates."""
        self.tag_model.create({"name": "Global Tag", "category": "general"})
        with self.assertRaises(ValidationError):
            self.tag_model.create({"name": "Global Tag", "category": "general"})

    def test_duplicate_company_tag_blocked(self):
        """Two tags in the same company with same name+category are duplicates."""
        company = self._make_company("Company A")
        self.tag_model.create({"name": "Co Tag", "category": "project", "company_id": company.id})
        with self.assertRaises(ValidationError):
            self.tag_model.create({"name": "Co Tag", "category": "project", "company_id": company.id})

    def test_same_name_different_category_allowed(self):
        self.tag_model.create({"name": "Alpha", "category": "general"})
        self.tag_model.create({"name": "Alpha", "category": "project"})

    def test_same_name_different_company_allowed(self):
        company_a = self._make_company("Company A")
        company_b = self._make_company("Company B")
        self.tag_model.create({"name": "Shared", "category": "general", "company_id": company_a.id})
        # Same name in a different company is allowed (company isolation).
        self.tag_model.create({"name": "Shared", "category": "general", "company_id": company_b.id})

    def test_global_and_company_tag_can_coexist(self):
        company = self._make_company("Company A")
        self.tag_model.create({"name": "Bridge", "category": "general"})  # global
        self.tag_model.create({"name": "Bridge", "category": "general", "company_id": company.id})

    def test_update_tag_preserves_uniqueness(self):
        tag = self.tag_model.create({"name": "Original", "category": "general"})
        self.tag_model.create({"name": "Other", "category": "general"})
        with self.assertRaises(ValidationError):
            tag.write({"name": "Other"})
