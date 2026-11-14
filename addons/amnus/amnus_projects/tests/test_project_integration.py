# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import AmnusProjectTestMixin


@tagged("standard", "amnus_projects", "at_install", "-post_install")
class TestAmnusProjectIntegration(AmnusProjectTestMixin, common.TransactionCase):
    """AMNUS fields on standard projects and the request relationship."""

    def test_amnus_project_defaults(self):
        project = self._create_project("Ordinary Project")
        self.assertFalse(project.amnus_is_amnus_project)
        self.assertFalse(project.amnus_request_id)
        self.assertEqual(project.amnus_deliverable_count, 0)

    def test_create_amnus_project_with_tags_and_deliverables(self):
        tag = self.env["amnus.tag"].create({"name": "Discovery", "category": "project"})
        project = self._create_project(
            "AMNUS Implementation",
            amnus_is_amnus_project=True,
            amnus_tag_ids=[(6, 0, [tag.id])],
            amnus_actual_go_live="2026-07-15",
            date_start="2026-01-05",
            date="2026-06-30",
        )
        deliverable = self._create_deliverable(project, "Functional spec")
        self.assertTrue(project.amnus_is_amnus_project)
        self.assertEqual(project.amnus_tag_ids, tag)
        self.assertEqual(project.amnus_actual_go_live, fields.Date.to_date("2026-07-15"))
        self.assertEqual(project.amnus_deliverable_ids, deliverable)
        self.assertEqual(project.amnus_deliverable_count, 1)

    def test_request_relationship_and_related_type(self):
        lead, request = self._create_approved_request(request_type="migration")
        project = self._create_project(
            "Migration Project",
            amnus_is_amnus_project=True,
            amnus_request_id=request.id,
        )
        self.assertEqual(project.amnus_request_id, request)
        self.assertEqual(project.amnus_request_type, "migration")
        self.assertEqual(request.project_id, project)
        self.assertEqual(request.project_count, 1)

    def test_duplicate_project_for_request_is_rejected(self):
        lead, request = self._create_approved_request()
        self._create_project("First Project", amnus_request_id=request.id)
        with self.assertRaises(ValidationError):
            self._create_project("Second Project", amnus_request_id=request.id)

    def test_unapproved_request_cannot_be_linked_at_create(self):
        lead, request = self._create_approved_request(state="draft")
        with self.assertRaises(ValidationError):
            self._create_project("Forbidden Project", amnus_request_id=request.id)

    def test_request_link_is_not_directly_editable(self):
        lead, request = self._create_approved_request()
        other_lead, other_request = self._create_approved_request(
            lead_name="Second Opportunity"
        )
        project = self._create_project("Linked Project", amnus_request_id=request.id)
        from odoo.exceptions import UserError

        with self.assertRaises(UserError):
            project.with_user(self.project_manager).write(
                {"amnus_request_id": other_request.id}
            )

    def test_deliverable_count_multiple(self):
        project = self._create_project("Counted Project", amnus_is_amnus_project=True)
        self._create_deliverable(project, "One")
        self._create_deliverable(project, "Two")
        self._create_deliverable(project, "Three")
        self.assertEqual(project.amnus_deliverable_count, 3)

    def test_project_with_accepted_deliverable_cannot_be_deleted(self):
        from odoo.exceptions import UserError

        project = self._create_project("Protected Project", amnus_is_amnus_project=True)
        deliverable = self._create_deliverable(project)
        deliverable.action_submit()
        deliverable.action_accept()
        with self.assertRaises(UserError):
            project.with_user(self.project_manager).unlink()
        self.assertTrue(project.exists())

    def test_project_can_still_be_deleted_without_accepted_deliverables(self):
        project = self._create_project("Temporary Project")
        self._create_deliverable(project, "Draft only")
        project.with_user(self.project_manager).unlink()
        self.assertFalse(project.exists())
