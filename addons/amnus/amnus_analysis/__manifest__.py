# -*- coding: utf-8 -*-
{
    "name": "AMNUS Analysis",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "AMNUS Requirements Analysis & Functional Analysis",
    "description": """
AMNUS Analysis
==============

Requirements management layer for the AMNUS Odoo Project Lifecycle Management Platform.

This addon provides structured requirements discovery and functional analysis for
Odoo implementation projects:

* Business, functional and non-functional requirements (``amnus.analysis.requirement``)
* Discovery workshops (``amnus.analysis.workshop``)
* AS-IS / TO-BE business process documentation (``amnus.analysis.process``)

Requirements are linked to an implementation project and carry a full lifecycle:
draft, under review, approved, rejected and cancelled. Approved requirements are
protected from silent rewrites and can only be changed through a controlled
revision (return-to-review) workflow.

Requirement traceability links requirements to the implementation work that
realizes them (project tasks, Agile user stories, deliverables) without
duplicating the standard Odoo execution model or the AMNUS Agile planning model.

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
        "security/amnus_analysis_groups.xml",
        "security/amnus_analysis_security.xml",
        "security/ir.model.access.csv",
        "data/amnus_analysis_sequence.xml",
        "views/amnus_analysis_requirement_views.xml",
        "views/amnus_analysis_workshop_views.xml",
        "views/amnus_analysis_process_views.xml",
        "views/amnus_analysis_menus.xml",
    ],
    "demo": [],
    "test": [
        "tests/test_requirement.py",
        "tests/test_workshop.py",
        "tests/test_process.py",
        "tests/test_security.py",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
