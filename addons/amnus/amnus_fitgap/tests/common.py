# -*- coding: utf-8 -*-
"""Shared fixtures for AMNUS Fit-Gap tests."""

from odoo import fields


class AmnusFitgapTestMixin:
    """Create the standard users, project and groups used by the Fit-Gap suite."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.fitgap_user_group = cls.env.ref("amnus_fitgap.group_amnus_fitgap_user")
        cls.fitgap_manager_group = cls.env.ref("amnus_fitgap.group_amnus_fitgap_manager")
        cls.fitgap_admin_group = cls.env.ref("amnus_fitgap.group_amnus_fitgap_admin")
        cls.fitgap_user = cls._create_user(
            "AMNUS Fit-Gap User", "amnus_fitgap_user_test", cls.fitgap_user_group
        )
        cls.fitgap_manager = cls._create_user(
            "AMNUS Fit-Gap Manager", "amnus_fitgap_manager_test", cls.fitgap_manager_group
        )
        cls.fitgap_admin = cls._create_user(
            "AMNUS Fit-Gap Admin", "amnus_fitgap_admin_test", cls.fitgap_admin_group
        )

    @classmethod
    def _create_user(cls, name, login, group):
        base_group = cls.env.ref("base.group_user")
        return cls.env["res.users"].create(
            {
                "name": name,
                "login": login,
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [base_group.id, group.id])],
            }
        )

    @classmethod
    def _rel_id(cls, value):
        return value.id if hasattr(value, "id") else value

    RELATIONAL_KEYS = (
        "project_id",
        "requirement_id",
        "assessor_id",
        "reviewer_id",
        "company_id",
        "user_id",
    )

    @classmethod
    def _normalise_relations(cls, values):
        vals = dict(values)
        for key in cls.RELATIONAL_KEYS:
            if key in vals:
                vals[key] = cls._rel_id(vals[key])
        return vals

    @classmethod
    def _create_project(cls, name="AMNUS Fit-Gap Project", **values):
        vals = {
            "name": name,
            "company_id": cls._rel_id(cls.company),
        }
        vals.update(values)
        return cls.env["project.project"].create(vals)

    @classmethod
    def _create_requirement(cls, project, **values):
        vals = {
            "name": values.pop("name", "Fit-Gap Requirement"),
            "project_id": cls._rel_id(project),
        }
        vals.update(values)
        requirement = cls.env["amnus.analysis.requirement"].create(
            cls._normalise_relations(vals)
        )
        return requirement

    @classmethod
    def _approve_requirement(cls, requirement, manager=None):
        manager = manager or cls.fitgap_manager
        requirement.with_user(cls.fitgap_user).action_submit_for_review()
        requirement.with_user(manager).action_approve()
        return requirement

    @classmethod
    def _create_approved_requirement(cls, project, **values):
        requirement = cls._create_requirement(project, **values)
        cls._approve_requirement(requirement)
        return requirement

    @classmethod
    def _create_assessment(cls, requirement, **values):
        vals = {
            "name": values.pop("name", "Fit-Gap Assessment"),
            "requirement_id": cls._rel_id(requirement),
        }
        vals.update(values)
        return cls.env["amnus.fitgap.assessment"].create(
            cls._normalise_relations(vals)
        )
