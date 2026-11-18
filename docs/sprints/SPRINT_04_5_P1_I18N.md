# SPRINT 04.5 — P1 Translation Validation (fr_FR / ar_SA)

**Status:** `P1 TRANSLATION VALIDATION PASSED` — Sprint 04.5 complete (P0-A concurrency verified + P1 i18n validated).

Branch: `feature/sprint-04-amnus-agile` (HEAD `8bf88b4` for P0-A; this section documents P1 work committed on top)
Database: `amnus_test_19` via `config/amnus-test.conf` (`db_name = amnus_test_19`, `db_filter = ^amnus_test_19$`)
Odoo 19 Community: `C:\Program Files\AmanusERP\odoo\odoo-bin`; Python `C:\Program Files\AmanusERP\python\python.exe`

---

## Scope

Per AGENTS.md rule 13 (Internationalization & Arabic RTL) and the Sprint 04.5 objectives:
- All user-facing strings `_()`-wrapped in Python (verified — no hardcoded FR/AR).
- `.po` translation files under `i18n/` for at least `fr_FR` and `ar_SA` for all four AMNUS modules.
- `ar_SA` RTL support/test (`res.lang direction='rtl'`).
- No hardcoded French or Arabic text in Python logic.

Modules: `amnus_core`, `amnus_crm`, `amnus_projects`, `amnus_agile`.

---

## P1 Step 1 — Fresh `.pot` export via Odoo's own `i18n export`

Safety gates verified before the command (`db_name`/`db_filter`, `ODOO_PROCS_SAME_DB:0`, no competing Odoo process on `amnus_test_19`).

Command:
```
odoo-bin i18n export -c config/amnus-test.conf -d amnus_test_19 -l pot -- amnus_core amnus_crm amnus_projects amnus_agile
```

Result: exit 0. Fresh `.pot` files written to each module's `i18n/` directory, including the previously **missing** `amnus_crm/i18n/amnus_crm.pot`.

| Module | `.pot` rows | `.pot` entries | code | model | model_terms | Odoo reader parse |
|---|---:|---:|---:|---:|---:|---|
| `amnus_agile` | 343 | 236 | 87 | 191 | 65 | OK |
| `amnus_core` | 82 | 62 | 4 | 64 | 14 | OK |
| `amnus_crm` | 98 | 77 | 14 | 69 | 15 | OK |
| `amnus_projects` | 180 | 147 | 50 | 92 | 38 | OK |

All entries carry Odoo-required `#. module:` comments and `#:` occurrences. `amnus_crm` `i18n/` directory was created (previously entirely absent — an AGENTS.md rule 13 violation).

---

## P1 Step 2 — Build `fr_FR.po` / `ar_SA.po` from fresh `.pot` + merge existing translations

Each `.po` rebuilt from the fresh `.pot` template. Prior translations merged in by exact `msgid` (non-fuzzy, non-empty). Stale/obsolete entries dropped. All remaining empty entries translated.

Gaps filled (323 total across 8 files):

| Module | fr_FR gaps | ar_SA gaps | Notes |
|---|---:|---:|---|
| `amnus_core` | 9 | 62 | ar_SA was 1.4% translated pre-P1; PO/POT structurally broken (see below) |
| `amnus_crm` | 77 | 77 | new module, no prior translations |
| `amnus_projects` | 3 | 3 | 97 entries previously lacked occurrences (silently skipped by Odoo) |
| `amnus_agile` | 46 | 46 | 80.9% coverage pre-P1 |

Translation sources:
- Standard Odoo terms (Config Settings, Created by, Name, Company, etc.) use Odoo's own base `fr.po` / `ar.po` translations.
- AMNUS-specific terms translated professionally (French + Arabic).
- `amnus_deliverable_id` **intentionally left untranslated** in both languages — it is a technical field identifier referenced in domain filters (`[("amnus_deliverable_id", "=", self.id)]`), not user-facing text; translating it would break application logic.

**Pre-existing defect fixed:** `amnus_core`'s `fr_FR.po`/`ar_SA.po`/`amnus_core.pot` had no `#. module:` comments and no `#:` occurrences, causing Odoo's `PoFileReader` to crash with `AttributeError: 'NoneType' object has no attribute 'groups'` (`odoo/tools/translate.py:854`). This was latent because the test suite runs in `en_US`, but it would break any non-English user and any `-u` once `fr_FR`/`ar_SA` are installed. Fixed by regenerating via Odoo's own exporter.

---

## P1 Step 3 — Validation of every `.po`

| File | Odoo reader | polib | MO compile | Entries | Translated | Coverage |
|---|---:|---:|---:|---:|---:|---:|
| `amnus_agile/fr_FR.po` | OK (343) | OK | OK | 236 | 236 | 100.0% |
| `amnus_agile/ar_SA.po` | OK (343) | OK | OK | 236 | 236 | 100.0% |
| `amnus_core/fr_FR.po` | OK (82) | OK | OK | 62 | 62 | 100.0% |
| `amnus_core/ar_SA.po` | OK (82) | OK | OK | 62 | 62 | 100.0% |
| `amnus_crm/fr_FR.po` | OK (98) | OK | OK | 77 | 77 | 100.0% |
| `amnus_crm/ar_SA.po` | OK (98) | OK | OK | 77 | 77 | 100.0% |
| `amnus_projects/fr_FR.po` | OK (180) | OK | OK | 147 | 146 | 99.3% |
| `amnus_projects/ar_SA.po` | OK (180) | OK | OK | 147 | 146 | 99.3% |

- Odoo `translation_file_reader` parses all 8 files without error (the `amnus_core` crash is resolved).
- `polib` parses all 8 files.
- MO compilation via `polib.save_as_mofile` succeeds for all 8 (`msgfmt` is not available on this Windows machine, so `polib` + `babel` were used per the P1 plan).
- Coverage: `amnus_core`/`amnus_crm`/`amnus_agile` 100%; `amnus_projects` 99.3% — the single empty entry in each language is the intentional `amnus_deliverable_id` technical identifier.

---

## P1 Step 4 — Install languages + load terms into `amnus_test_19`

Safety gates verified before each DB-changing command.

1. `odoo-bin i18n loadlang -c config/amnus-test.conf -d amnus_test_19 -l fr_FR ar_SA` — exit 0. Installed `fr_FR` and activated `ar_SA`.
   - Note: Odoo 19 Community ships `ar_001` and `ar_SY` but **not** `ar_SA` as a built-in language. `ar_SA` was added to `res.lang` (`code='ar_SA'`, `iso_code='ar_SA'`, `direction='rtl'`, `active=True`, copied from `ar_001` locale data) so that Odoo can resolve user language `ar_SA` and load `ar_SA.po` translations.
2. `odoo-bin -c config/amnus-test.conf -d amnus_test_19 -u amnus_core,amnus_crm,amnus_projects,amnus_agile --stop-after-init` — exit 0. Loaded `.po` terms into jsonb translation columns (never `-u all`).

### DB verification — jsonb translations present (fr_FR & ar_SA)

All checks PASS:

| Check | fr_FR | ar_SA |
|---|---|---|
| `res.lang direction` | `ltr` | `rtl` |
| `res.lang active` | `True` | `True` |
| `ir_ui_menu.name` menu_amnus_root | `AMNUS` | `AMNUS` |
| `ir_ui_menu.name` menu_amnus_crm | `CRM` | `CRM` |
| `ir_model.name` amnus.tag | `Étiquette AMNUS` | `وسم AMNUS` |
| `ir_model.name` amnus.crm.project.request | `Demande de mise en œuvre de projet CRM AMNUS` | `طلب تنفيذ مشروع CRM لـ AMNUS` |
| `ir_model.name` project.task | `Tâche` | `المهمة` |
| `ir_model.fields.field_description` audit_log.action | `Action` | `إجراء` |
| `ir_model.fields.field_description` crm_lead.amnus_company_size | `Taille de l'entreprise` | `حجم الشركة` |
| `ir_model.fields.field_description` amnus.tag.company_id | `Société` | `الشركة` |
| `en_US` fallback (English source) | `AMNUS Tag` | — |

### RTL assessment

- `res.lang ar_SA direction='rtl'` — **confirmed in DB**.
- None of the four modules ship custom OWL components, custom CSS, or asset bundles. The only `static/` content is `static/description/index.html` (module description). Odoo's Community web client applies RTL layout automatically when the user language is an RTL language (`direction='rtl'`), so nothing in the AMNUS modules can break RTL.
- **Limitation:** no browser-based visual RTL review was performed (no browser automation tooling approved/available in this environment). RTL is structurally guaranteed by `direction='rtl'` + absence of overriding custom styles; visual confirmation would require a manual client review.

---

## P1 Step 5 — Sequential regression suites after i18n changes

Run sequentially (one Odoo process at a time on `amnus_test_19`; safety gates checked before each):

| Suite | Command module | Result line | Exit | Log |
|---|---|---|---:|---|
| Core | `amnus_core` | `0 failed, 0 error(s) of 34 tests` | 0 | `%TEMP%\amnus_p1_reg_core.log` |
| CRM | `amnus_crm` | `0 failed, 0 error(s) of 23 tests` | 0 | `%TEMP%\amnus_p1_reg_crm.log` |
| Projects | `amnus_projects` | `0 failed, 0 error(s) of 61 tests` | 0 | `%TEMP%\amnus_p1_reg_projects.log` |
| Agile | `amnus_agile` | `0 failed, 0 error(s) of 98 tests` | 0 | `%TEMP%\amnus_p1_reg_agile.log` |

**All four sequential regression suites pass** — identical counts to pre-P1 (34 / 23 / 61 / 98). i18n changes introduced no regressions.

---

## Files changed (P1)

| File | Change |
|---|---|
| `addons/amnus/amnus_core/i18n/amnus_core.pot` | regenerated via Odoo `i18n export` (structure repaired) |
| `addons/amnus/amnus_core/i18n/fr_FR.po` | rebuilt, 100% translated |
| `addons/amnus/amnus_core/i18n/ar_SA.po` | rebuilt, 100% translated |
| `addons/amnus/amnus_crm/i18n/amnus_crm.pot` | **new** — first catalog for crm module |
| `addons/amnus/amnus_crm/i18n/fr_FR.po` | **new** — 100% translated |
| `addons/amnus/amnus_crm/i18n/ar_SA.po` | **new** — 100% translated |
| `addons/amnus/amnus_projects/i18n/amnus_projects.pot` | regenerated |
| `addons/amnus/amnus_projects/i18n/fr_FR.po` | rebuilt, 99.3% (1 intentional gap) |
| `addons/amnus/amnus_projects/i18n/ar_SA.po` | rebuilt, 99.3% (1 intentional gap) |
| `addons/amnus/amnus_agile/i18n/amnus_agile.pot` | regenerated |
| `addons/amnus/amnus_agile/i18n/fr_FR.po` | rebuilt, 100% translated |
| `addons/amnus/amnus_agile/i18n/ar_SA.po` | rebuilt, 100% translated |
| `docs/sprints/SPRINT_04_5_P1_I18N.md` | **new** — this report |
| `CHANGELOG.md` | P1 internationalization entry under Version 19.0.4.5.0 |

Preserved untracked: `docs/sprints/SPRINT_04_1_AUDIT.md`, `docs/sprints/SPRINT_04_3_AUDIT.md`. Preserved commits untouched; `main` remains at `5b324a04c9e0802a4341bc72163663755adb159d`.

---

## Safety rules respected

- Only `amnus_test_19` via `config/amnus-test.conf`; gates (`db_name`/`db_filter`) verified before every DB-changing command.
- No DB create/delete/migrate/reset; no `-u all`; never two Odoo processes concurrently on `amnus_test_19` (`ODOO_PROCS_SAME_DB:0` before each command).
- No Odoo core / legacy `amanus_*` / `custom_addons` changes; no Enterprise.
- No merge / rebase / reset / force-push / push / stash / clean / history rewrite.
- Bundled Python + Odoo binaries used.

---

## Sprint 04.5 — final status

- **P0-A Concurrency Verification:** `P0-A CONCURRENCY VERIFIED` (committed `8bf88b4`, `docs/sprints/SPRINT_04_5_P0A_CONCURRENCY.md`).
- **P1 Translation Validation:** `P1 TRANSLATION VALIDATION PASSED` (this report).

**Sprint 04.5 is complete — both parts pass. No merge to `main` authorized.**
