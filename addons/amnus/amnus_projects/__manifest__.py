# -*- coding: utf-8 -*-
{
    "name": "AMNUS Projects",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "AMNUS Project Lifecycle Management for Odoo Implementation Projects",
    "description": """
AMNUS Projects
==============

Project lifecycle foundation for the AMNUS Odoo Project Lifecycle Management
Platform.

This addon extends standard Odoo Project functionality (it does not replace it):

* Converts an approved CRM implementation request into a real project.
* Adds AMNUS lifecycle metadata to ``project.project``.
* Adds a deliverable model with a controlled acceptance workflow.
* Links tasks to deliverables with project consistency validation.
* Integrates with AMNUS tags, audit logging and security groups.

Standard project stages, task stages, task states and project health are reused
as-is. No duplicate project, task, stage or state models are created.

Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "amnus_core",
        "amnus_crm",
        "project",
        "mail",
    ],
    "data": [
        "security/amnus_projects_groups.xml",
        "security/amnus_projects_security.xml",
        "security/ir.model.access.csv",
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/amnus_project_deliverable_views.xml",
        "views/amnus_crm_project_request_views.xml",
        "views/amnus_projects_menus.xml",
    ],
    "demo": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
