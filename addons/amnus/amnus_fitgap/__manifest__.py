# -*- coding: utf-8 -*-
{
    "name": "AMNUS Fit-Gap",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "AMNUS Fit-Gap & Solution Design for Odoo Implementation Projects",
    "description": """
AMNUS Fit-Gap
==============

Fit-Gap and Solution Design layer for the AMNUS Odoo Project Lifecycle Management Platform.

This addon provides structured assessment of approved business requirements against the
standard capabilities of Odoo 19 Community Edition:

* Fit-Gap assessment (``amnus.fitgap.assessment``) — assesses each approved requirement
  against standard Odoo capabilities and records the implementation approach.
* Immutable assessment versions (``amnus.fitgap.assessment.version``) — preserves the
  exact approved assessment content for audit and traceability.

Each assessment carries:
* Outcome classification (standard fit, configuration, custom development, integration,
  workaround, not supported, deferred, requires analysis).
* Standard Odoo capability reference (module, feature, behavior description).
* Gap analysis (gap description, root cause, business/technical impact).
* Implementation approach (configuration, development, integration, workaround, proposed
  solution, technical notes, dependencies, assumptions).
* Effort estimation (functional analysis, configuration, development, integration,
  testing — with computed total).
* Risk level and estimation confidence.
* Decision rationale and approval metadata.
* Evidence attachments (native Odoo ``ir.attachment``).

Assessments follow a controlled lifecycle (draft, in analysis, under review, approved,
rejected, superseded, cancelled) with immutable version snapshots on approval.

Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "amnus_core",
        "amnus_analysis",
    ],
    "data": [
        "security/amnus_fitgap_groups.xml",
        "security/amnus_fitgap_security.xml",
        "security/ir.model.access.csv",
        "data/amnus_fitgap_sequence.xml",
        "views/amnus_fitgap_assessment_views.xml",
        "views/amnus_fitgap_reject_wizard_views.xml",
        "views/amnus_fitgap_menus.xml",
    ],
    "demo": [],
    "test": [
        "tests/test_installation.py",
        "tests/test_assessment.py",
        "tests/test_workflow.py",
        "tests/test_security.py",
        "tests/test_version.py",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
