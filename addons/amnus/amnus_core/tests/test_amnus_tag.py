# -*- coding: utf-8 -*-
from odoo.tests import common
from odoo.exceptions import ValidationError


class TestAmnusTag(common.TransactionCase):
    """Tests for the AMNUS Tag shared model."""

    def setUp(self):
        super().setUp()
        self.tag_model = self.env["amnus.tag"]

    def test_create_tag(self):
        tag = self.tag_model.create({"name": "Test Tag", "category": "project"})
        self.assertTrue(tag.id)
        self.assertEqual(tag.name, "Test Tag")
        self.assertEqual(tag.category, "project")
        self.assertTrue(tag.active)

    def test_required_name(self):
        with self.assertRaises(ValidationError):
            self.tag_model.create({"category": "project"})

    def test_empty_name_rejected(self):
        with self.assertRaises(ValidationError):
            self.tag_model.create({"name": "   ", "category": "project"})

    def test_duplicate_prevention_same_company(self):
        self.tag_model.create({"name": "Unique Tag", "category": "general"})
        with self.assertRaises(Exception):
            self.tag_model.create({"name": "Unique Tag", "category": "general"})

    def test_archive_tag(self):
        tag = self.tag_model.create({"name": "Archive Me"})
        tag.action_archive()
        self.assertFalse(tag.active)

    def test_search_behavior(self):
        self.tag_model.create({"name": "Searchable Tag", "category": "analysis"})
        tags = self.tag_model.search([("name", "ilike", "Searchable")])
        self.assertEqual(len(tags), 1)
