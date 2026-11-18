# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged

from .common import AmnusAgileTestMixin


@tagged("standard", "amnus_agile", "at_install", "-post_install")
class TestAmnusAgileSecurity(AmnusAgileTestMixin, common.TransactionCase):
    """Agile group hierarchy, ACLs, record rules and cross-company isolation."""

    def setUp(self):
        super().setUp()
        self.project = self._create_project("Agile Security Project")

    def test_group_hierarchy(self):
        self.assertTrue(self.agile_user.has_group("amnus_agile.group_amnus_agile_user"))
        self.assertTrue(self.agile_manager.has_group("amnus_agile.group_amnus_agile_manager"))
        self.assertTrue(self.agile_admin.has_group("amnus_agile.group_amnus_agile_admin"))
        self.assertTrue(self.agile_user.has_group("amnus_core.group_amnus_user"))
        self.assertTrue(self.agile_user.has_group("amnus_projects.group_amnus_project_user"))
        self.assertTrue(self.agile_manager.has_group("amnus_projects.group_amnus_project_manager"))
        self.assertTrue(self.agile_admin.has_group("amnus_projects.group_amnus_project_manager"))

    def test_agile_groups_are_not_auto_assigned(self):
        user = self.env["res.users"].create(
            {
                "name": "Plain Agile User",
                "login": "plain_agile_user_test",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertFalse(user.has_group("amnus_agile.group_amnus_agile_user"))

    def test_agile_user_cannot_manage_sprints(self):
        sprint_model = self.env["amnus.agile.sprint"].with_user(self.agile_user)
        self.assertTrue(sprint_model.has_access("read"))
        self.assertFalse(sprint_model.has_access("create"))
        self.assertFalse(sprint_model.has_access("write"))
        self.assertFalse(sprint_model.has_access("unlink"))

    def test_agile_manager_can_manage_sprints(self):
        sprint_model = self.env["amnus.agile.sprint"].with_user(self.agile_manager)
        self.assertTrue(sprint_model.has_access("create"))
        self.assertTrue(sprint_model.has_access("write"))
        self.assertTrue(sprint_model.has_access("unlink"))

    def test_agile_user_cannot_write_burndown_metrics(self):
        burndown_model = self.env["amnus.agile.burndown"].with_user(self.agile_user)
        self.assertTrue(burndown_model.has_access("read"))
        self.assertFalse(burndown_model.has_access("create"))
        self.assertFalse(burndown_model.has_access("write"))
        self.assertFalse(burndown_model.has_access("unlink"))

    def test_membership_history_is_not_client_writable(self):
        membership_model = self.env["amnus.agile.sprint.membership"].with_user(
            self.agile_manager
        )
        self.assertTrue(membership_model.has_access("read"))
        self.assertFalse(membership_model.has_access("create"))
        self.assertFalse(membership_model.has_access("write"))
        self.assertFalse(membership_model.has_access("unlink"))

    def test_agile_user_cannot_create_epic(self):
        epic_model = self.env["amnus.agile.epic"].with_user(self.agile_user)
        self.assertTrue(epic_model.has_access("read"))
        self.assertFalse(epic_model.has_access("create"))

    # ------------------------------------------------------------------
    # Cross-company isolation
    # ------------------------------------------------------------------
    def test_cross_company_story_is_hidden(self):
        company_a = self.env["res.company"].create({"name": "Agile Company A"})
        company_b = self.env["res.company"].create({"name": "Agile Company B"})
        project_a = self._create_project("Agile Company A Project", company_id=company_a.id)
        story_a = self._create_story(project_id=project_a)

        user_b = self.env["res.users"].create(
            {
                "name": "Agile Company B User",
                "login": "agile_company_b_user",
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
                "group_ids": [(6, 0, [self.agile_user_group.id])],
            }
        )
        # Follow the project so that only the company rule (not the project
        # visibility rule) can hide the story.
        project_a.message_subscribe(partner_ids=[user_b.partner_id.id])
        found = self.env["amnus.agile.user.story"].with_user(user_b).search(
            [("id", "=", story_a.id)]
        )
        self.assertFalse(found, "Cross-company stories must be hidden")
        with self.assertRaises(AccessError):
            story_a.with_user(user_b).read(["name"])

    def test_multi_company_user_can_read_allowed_company(self):
        company_a = self.env["res.company"].create({"name": "Agile Multi Company A"})
        company_b = self.env["res.company"].create({"name": "Agile Multi Company B"})
        project_a = self._create_project(
            "Agile Multi Company Project", company_id=company_a.id
        )
        story_a = self._create_story(project_id=project_a)
        user = self.env["res.users"].create(
            {
                "name": "Agile Multi Company User",
                "login": "agile_multi_company_user",
                "company_id": company_a.id,
                "company_ids": [(6, 0, [company_a.id, company_b.id])],
                "group_ids": [(6, 0, [self.agile_user_group.id])],
            }
        )
        project_a.message_subscribe(partner_ids=[user.partner_id.id])
        self.assertEqual(
            self.env["amnus.agile.user.story"].with_user(user).search(
                [("id", "=", story_a.id)]
            ),
            story_a,
        )

    # ------------------------------------------------------------------
    # Identity protection
    # ------------------------------------------------------------------
    def test_user_cannot_forge_story_state(self):
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).write({"state": "done"})
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).action_plan()
        self.assertEqual(story.state, "backlog")

    def test_user_cannot_add_or_remove_story_from_sprint(self):
        sprint = self._create_sprint(project_id=self.project.id)
        story = self._create_story(project_id=self.project.id)
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).action_add_to_sprint(sprint.id)
        self.assertFalse(story.sprint_id)
        story.with_user(self.agile_manager).action_add_to_sprint(sprint.id)
        self.assertEqual(story.sprint_id, sprint)
        with self.assertRaises(UserError):
            story.with_user(self.agile_user).action_remove_from_sprint()
        self.assertEqual(story.sprint_id, sprint)

    def test_user_cannot_carry_over_stories(self):
        source = self._create_sprint(project_id=self.project.id, name="Carry Security Source")
        target = self._create_sprint(project_id=self.project.id, name="Carry Security Target")
        story = self._create_story(
            project_id=self.project.id, sprint_id=source.id, state="planned"
        )
        source.with_user(self.agile_manager).action_plan()
        source.with_user(self.agile_manager).action_start()
        with self.assertRaises(UserError):
            source.with_user(self.agile_user).action_carry_over([story.id], target.id)
        self.assertEqual(story.sprint_id, source)
