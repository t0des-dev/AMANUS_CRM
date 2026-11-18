# -*- coding: utf-8 -*-
"""Shared fixtures for AMNUS Agile tests."""


class AmnusAgileTestMixin:
    """Create the standard users and groups used by the Agile test suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.agile_user_group = cls.env.ref("amnus_agile.group_amnus_agile_user")
        cls.agile_manager_group = cls.env.ref("amnus_agile.group_amnus_agile_manager")
        cls.agile_admin_group = cls.env.ref("amnus_agile.group_amnus_agile_admin")
        cls.agile_user = cls._create_user(
            "AMNUS Agile User", "amnus_agile_user_test", cls.agile_user_group
        )
        cls.agile_manager = cls._create_user(
            "AMNUS Agile Manager",
            "amnus_agile_manager_test",
            cls.agile_manager_group,
        )
        cls.agile_admin = cls._create_user(
            "AMNUS Agile Admin", "amnus_agile_admin_test", cls.agile_admin_group
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

    @staticmethod
    def _rel_id(value):
        """Accept either a record or an integer id for a relational value."""
        return value.id if hasattr(value, "id") else value

    RELATIONAL_KEYS = (
        "project_id",
        "epic_id",
        "sprint_id",
        "task_id",
        "company_id",
        "user_id",
    )

    def _normalise_relations(self, values):
        """Replace recordset relational values with their database ids."""
        vals = dict(values)
        for key in self.RELATIONAL_KEYS:
            if key in vals:
                vals[key] = self._rel_id(vals[key])
        return vals

    def _create_project(self, name="AMNUS Agile Project", **values):
        vals = {
            "name": name,
            "company_id": self._rel_id(self.company),
        }
        vals.update(values)
        return self.env["project.project"].create(vals)

    def _create_story(self, **values):
        vals = {"name": values.pop("name", "Agile User Story")}
        vals.update(values)
        return self.env["amnus.agile.user.story"].create(
            self._normalise_relations(vals)
        )

    def _create_epic(self, **values):
        vals = {"name": values.pop("name", "Agile Epic")}
        vals.update(values)
        return self.env["amnus.agile.epic"].create(self._normalise_relations(vals))

    def _create_sprint(self, **values):
        vals = {
            "name": values.pop("name", "Sprint 1"),
            "date_start": values.pop("date_start", "2026-01-05"),
            "date_end": values.pop("date_end", "2026-01-18"),
        }
        vals.update(values)
        return self.env["amnus.agile.sprint"].create(self._normalise_relations(vals))
