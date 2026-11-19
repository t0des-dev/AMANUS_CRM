# -*- coding: utf-8 -*-
"""Shared fixtures for AMNUS Analysis tests."""


class AmnusAnalysisTestMixin:
    """Create the standard users, project and groups used by the Analysis test suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.analysis_user_group = cls.env.ref("amnus_analysis.group_amnus_analysis_user")
        cls.analysis_manager_group = cls.env.ref(
            "amnus_analysis.group_amnus_analysis_manager"
        )
        cls.analysis_admin_group = cls.env.ref("amnus_analysis.group_amnus_analysis_admin")
        cls.analysis_user = cls._create_user(
            "AMNUS Analysis User", "amnus_analysis_user_test", cls.analysis_user_group
        )
        cls.analysis_manager = cls._create_user(
            "AMNUS Analysis Manager",
            "amnus_analysis_manager_test",
            cls.analysis_manager_group,
        )
        cls.analysis_admin = cls._create_user(
            "AMNUS Analysis Admin", "amnus_analysis_admin_test", cls.analysis_admin_group
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

    @classmethod
    def _rel_id(cls, value):
        """Accept either a record or an integer id for a relational value."""
        return value.id if hasattr(value, "id") else value

    RELATIONAL_KEYS = (
        "project_id",
        "task_id",
        "story_id",
        "deliverable_id",
        "owner_id",
        "analyst_id",
        "stakeholder_id",
        "facilitator_id",
        "company_id",
        "user_id",
    )

    @classmethod
    def _normalise_relations(cls, values):
        """Replace recordset relational values with their database ids."""
        vals = dict(values)
        for key in cls.RELATIONAL_KEYS:
            if key in vals:
                vals[key] = cls._rel_id(vals[key])
        return vals

    @classmethod
    def _create_project(cls, name="AMNUS Analysis Project", **values):
        vals = {
            "name": name,
            "company_id": cls._rel_id(cls.company),
        }
        vals.update(values)
        return cls.env["project.project"].create(vals)

    @classmethod
    def _create_task(cls, project, **values):
        vals = {
            "name": values.pop("name", "Analysis Task"),
            "project_id": cls._rel_id(project),
        }
        vals.update(values)
        return cls.env["project.task"].create(vals)

    @classmethod
    def _create_requirement(cls, project, **values):
        vals = {
            "name": values.pop("name", "Analysis Requirement"),
            "project_id": cls._rel_id(project),
        }
        vals.update(values)
        return cls.env["amnus.analysis.requirement"].create(
            cls._normalise_relations(vals)
        )

    @classmethod
    def _create_workshop(cls, project, **values):
        vals = {
            "name": values.pop("name", "Analysis Workshop"),
            "project_id": cls._rel_id(project),
            "date_start": values.pop("date_start", "2026-01-05 09:00:00"),
        }
        vals.update(values)
        return cls.env["amnus.analysis.workshop"].create(
            cls._normalise_relations(vals)
        )

    @classmethod
    def _create_process(cls, project, **values):
        vals = {
            "name": values.pop("name", "Analysis Process"),
            "project_id": cls._rel_id(project),
        }
        vals.update(values)
        return cls.env["amnus.analysis.process"].create(
            cls._normalise_relations(vals)
        )
