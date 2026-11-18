# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, tagged

from .common import AmnusAnalysisTestMixin


@tagged("standard", "amnus_analysis", "at_install", "-post_install")
class TestAmnusAnalysisWorkshop(AmnusAnalysisTestMixin, common.TransactionCase):
    """AMNUS Analysis workshop model tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls._create_project("Workshop Test Project")

    def test_workshop_creation(self):
        workshop = self._create_workshop(
            self.project,
            name="Requirements Discovery",
            workshop_type="discovery",
        )
        self.assertTrue(workshop.id)
        self.assertEqual(workshop.state, "draft")
        self.assertTrue(workshop.reference, "Reference must be generated")
        self.assertNotEqual(workshop.reference, "New")
        self.assertEqual(workshop.project_id, self.project)
        self.assertEqual(workshop.customer_id, self.project.partner_id)
        self.assertEqual(workshop.company_id, self.project.company_id)

    def test_workshop_created_in_draft_only(self):
        with self.assertRaises(UserError):
            self.env["amnus.analysis.workshop"].create(
                {
                    "name": "Invalid state",
                    "project_id": self.project.id,
                    "date_start": "2026-01-05 09:00:00",
                    "state": "held",
                }
            )

    def test_workshop_mark_held(self):
        workshop = self._create_workshop(self.project, name="Discovery Workshop")
        workshop.action_mark_held()
        self.assertEqual(workshop.state, "held")

    def test_workshop_cancel(self):
        workshop = self._create_workshop(self.project, name="Cancellable Workshop")
        workshop.action_cancel()
        self.assertEqual(workshop.state, "cancelled")

    def test_workshop_unlink_protected_when_held(self):
        workshop = self._create_workshop(self.project, name="Protected Workshop")
        workshop.action_mark_held()
        with self.assertRaises(UserError):
            workshop.unlink()

    def test_workshop_requirement_link(self):
        requirement = self._create_requirement(self.project, name="Workshop Requirement")
        workshop = self._create_workshop(
            self.project, name="Discovery Workshop", requirement_ids=[(6, 0, [requirement.id])]
        )
        self.assertIn(requirement, workshop.requirement_ids)

    def test_workshop_cross_project_requirement_rejected(self):
        other_project = self._create_project("Other Project")
        requirement = self._create_requirement(other_project, name="Other Requirement")
        with self.assertRaises(ValidationError):
            self._create_workshop(
                self.project,
                name="Cross-project Workshop",
                requirement_ids=[(6, 0, [requirement.id])],
            )
