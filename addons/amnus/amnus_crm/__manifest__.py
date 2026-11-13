{
    "name": "AMNUS CRM",
    "version": "19.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "AMNUS CRM — Customer Relationship Management for Odoo Implementation Projects",
    "description": """
AMNUS CRM
=========

CRM extension for the AMNUS Odoo Project Lifecycle Management Platform.

This addon extends standard Odoo CRM (``crm.lead``) with AMNUS-specific fields
for tracking Odoo implementation opportunities, and provides a structured
implementation request model for formal project handover.

Features:
* AMNUS implementation flag on leads/opportunities.
* Request type classification (new implementation, customization, migration, etc.).
* Implementation dates, estimated users, technical notes.
* AMNUS tags integration.
* Implementation request model with controlled workflow.
* Company isolation and AMNUS security groups.

Depends on: amnus_core, crm, contacts, mail.
Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "amnus_core",
        "crm",
        "contacts",
        "mail",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/crm_lead_views.xml",
        "views/amnus_crm_project_request_views.xml",
        "views/amnus_menus.xml",
    ],
    "demo": [],
    "application": True,
    "installable": True,
    "auto_install": False,
}
