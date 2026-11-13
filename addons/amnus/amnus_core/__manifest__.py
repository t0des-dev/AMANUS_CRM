{
    "name": "AMNUS Core",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "AMNUS Platform — Core Foundation",
    "description": """
AMNUS Core
==========

Shared infrastructure for all AMNUS (Odoo Project Lifecycle Management Platform) modules.

This module provides:
* Reusable tags (``amnus.tag``) for classifying records across AMNUS modules.
* A shared audit log (``amnus.audit.log``) for recording important business operations.
* Foundational AMNUS configuration via ``res.config.settings``.
* The AMNUS root menu and security groups (AMNUS User, Manager, Administrator).

It is the foundation layer of the AMNUS platform and must be installed before any
other AMNUS addon.

Odoo 19 Community Edition only. No Enterprise dependencies.
""",
    "author": "AMNUS",
    "website": "https://example.com/amnus",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_setup",
    ],
    "data": [
        "security/security.xml",
        "security/amnus_security.xml",
        "views/amnus_menu.xml",
        "views/amnus_tag_views.xml",
        "views/amnus_audit_log_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [],
    "test": [
        "tests/test_amnus_tag.py",
        "tests/test_amnus_audit_log.py",
        "tests/test_security.py",
        "tests/test_config.py",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
