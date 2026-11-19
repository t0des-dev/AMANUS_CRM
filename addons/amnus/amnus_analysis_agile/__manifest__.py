# -*- coding: utf-8 -*-
{
    "name": "AMNUS Analysis — Agile Integration",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "Optional Agile traceability for AMNUS Requirements Analysis",
    "description": """
AMNUS Analysis — Agile Integration
====================================

Optional integration between ``amnus_analysis`` and ``amnus_agile``.

Adds Agile user-story traceability to AMNUS requirements:

* ``story_id`` field on ``amnus.analysis.requirement`` linking to
  ``amnus.agile.user.story`` with project-consistency enforcement.
* Form view extension showing the linked story.

This addon is optional. ``amnus_analysis`` loads and functions fully without it.
Install this addon only when Agile traceability is needed.

Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "amnus_analysis",
        "amnus_agile",
    ],
    "data": [
        "views/amnus_analysis_requirement_agile_views.xml",
    ],
    "demo": [],
    "application": False,
    "installable": True,
    "auto_install": False,
}
