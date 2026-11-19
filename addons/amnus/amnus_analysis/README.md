# AMNUS Analysis

Requirements management layer for the AMNUS Odoo Project Lifecycle Management Platform.

This addon provides structured requirements discovery and functional analysis for Odoo implementation projects:

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

## Module manifest

* Name: AMNUS Analysis
* Version: 19.0.1.0.0
* Category: Services/Project
* License: LGPL-3
* Depends: amnus_core, amnus_projects, project, mail
* Application: True
* Auto install: False

## Models

| Model | Purpose |
|-------|---------|
| ``amnus.analysis.requirement`` | Customer business or functional requirement (requirement record) |
| ``amnus.analysis.workshop`` | Structured discovery workshop |
| ``amnus.analysis.process`` | AS-IS / TO-BE business process documentation |

## Security groups

| Group | XML ID | Implies |
|-------|--------|---------|
| AMNUS Analysis User | ``group_amnus_analysis_user`` | ``amnus_core.group_amnus_user`` |
| AMNUS Analysis Manager | ``group_amnus_analysis_manager`` | analysis user, ``amnus_projects.group_amnus_project_manager`` |
| AMNUS Analysis Administrator | ``group_amnus_analysis_admin`` | analysis manager |

Groups are never auto-assigned.

## Menus

Under *AMNUS → Analysis*:

* Requirements — list, kanban, form, search
* Workshops — list, form, search
* Business Processes — list, form, search

## Internationalization

* Translatable strings wrapped in ``_()``.
* ``i18n/amnus_analysis.pot`` (template), ``i18n/fr_FR.po``, ``i18n/ar_SA.po``.
* Arabic (ar_SA) requires RTL support; RTL relies on native Odoo web-client behavior (no custom OWL/CSS).

## Dependencies

* ``amnus_core`` — foundation, shared tags, audit log, security groups
* ``amnus_projects`` — project execution, deliverables
* ``project`` — standard Odoo Project (execution model, reused)
* ``mail`` — chatter

## Tests

Automated tests under ``tests/`` cover requirement creation, workflow transitions,
traceability, project/company consistency guards and security. Tests run under
``--test-enable``.

## Known limitations

* Portal-based customer approval is out of scope for this Sprint.
* No visual BPMN process designer; process documentation is text-based.
* Requirement references are globally unique (not project-scoped).
