# -*- coding: utf-8 -*-
"""Shared fixtures for AMNUS Projects tests."""


class AmnusProjectTestMixin:
    """Create the standard users and groups used by the test suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.project_user_group = cls.env.ref(
            "amnus_projects.group_amnus_project_user"
        )
        cls.project_manager_group = cls.env.ref(
            "amnus_projects.group_amnus_project_manager"
        )
        cls.project_admin_group = cls.env.ref(
            "amnus_projects.group_amnus_project_admin"
        )
        cls.project_user = cls._create_user(
            "AMNUS Project User", "amnus_project_user_test", cls.project_user_group
        )
        cls.project_manager = cls._create_user(
            "AMNUS Project Manager",
            "amnus_project_manager_test",
            cls.project_manager_group,
        )
        cls.project_admin = cls._create_user(
            "AMNUS Project Admin", "amnus_project_admin_test", cls.project_admin_group
        )

    @classmethod
    def _create_user(cls, name, login, group):
        return cls.env["res.users"].create(
            {
                "name": name,
                "login": login,
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [group.id])],
            }
        )

    def _create_approved_request(self, **values):
        lead = self.env["crm.lead"].create(
            {
                "name": values.pop("lead_name", "AMNUS Handover Opportunity"),
                "type": "opportunity",
                "partner_id": values.pop("partner_id", False),
                "company_id": self.company.id,
            }
        )
        vals = {
            "lead_id": lead.id,
            "company_id": self.company.id,
            "state": "approved",
            "request_type": "new_implementation",
            "user_id": self.project_manager.id,
            "scope_summary": "Implement Odoo for the customer.",
            "expected_start_date": "2026-01-05",
            "expected_go_live": "2026-06-30",
        }
        vals.update(values)
        request = self.env["amnus.crm.project.request"].create(vals)
        return lead, request

    def _create_project(self, name="AMNUS Project", **values):
        vals = {"name": name, "company_id": self.company.id}
        vals.update(values)
        return self.env["project.project"].create(vals)

    def _create_deliverable(self, project, name="Deliverable", **values):
        vals = {
            "name": name,
            "project_id": project.id,
            "type": "document",
            "responsible_id": self.project_user.id,
        }
        vals.update(values)
        return self.env["amnus.project.deliverable"].create(vals)
