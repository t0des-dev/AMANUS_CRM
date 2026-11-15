# -*- coding: utf-8 -*-
{
    "name": "AMNUS Agile",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "AMNUS Agile & Scrum Management for Odoo Implementation Projects",
    "description": """
AMNUS Agile
=============

Agile and Scrum management layer for the AMNUS Odoo Project Lifecycle Management Platform.

This addon provides planning artifacts that sit on top of the standard Odoo 19 Project
execution model (``project.task``) and the AMNUS deliverable acceptance model:

* Product backlog user stories (``amnus.agile.user.story``).
* Epics grouping user stories (``amnus.agile.epic``).
* Sprints with backlog, capacity, commitment, completion, review and retrospective
  (``amnus.agile.sprint``).
* Historical burndown points (``amnus.agile.burndown``).

The execution model remains the standard ``project.task``. User stories are planning
records that may link to a task; they never duplicate task stages, assignees or deadlines.

Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "amnus_core",
        "amnus_projects",
        "project",
        "mail",
    ],
    "data": [
        "security/amnus_agile_groups.xml",
        "security/amnus_agile_security.xml",
        "security/ir.model.access.csv",
        "views/amnus_agile_user_story_views.xml",
        "views/amnus_agile_epic_views.xml",
        "views/amnus_agile_carry_over_views.xml",
        "views/amnus_agile_sprint_views.xml",
        "views/amnus_agile_reporting_views.xml",
        "views/amnus_agile_menus.xml",
    ],
    "demo": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
