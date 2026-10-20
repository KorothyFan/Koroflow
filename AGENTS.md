# Hypit + Haiyi workflow repository

For video-production requests, read `skills/hypit-haiyi/SKILL.md` and use the unified Haiyi generation / Hypit composition workflow unless the user chooses another tool. Local paths are in `.local/config.json`; never assume the checkout path from a prior conversation.

Keep video projects separate from the tool and Provider installation. Use `scripts/workflow.mjs init` for new projects. Never replace an existing production with the demo prompt.

For integration development, use the commit pinned in `upstream.json`. Run `node scripts/workflow.mjs verify` after changing Provider behavior or execution/setup helpers. This performs offline mock tests and Source/plan validation, not paid generation. Check skill metadata with the installed skill-creator validator when available.

Never commit `.local`, credentials, node_modules, runtime databases or generated customer media. Keep package distribution source-only using `scripts/bundle.mjs`. Do not publish the repository or submit paid generation simply to validate installation.

Preserve upstream attribution and terms from `NOTICE.md` and `third-party/HYPIT-LICENSE`. Do not describe this integration as an official joint plugin or claim live generation was verified by mock tests.

For delivery records, production counts or publication planning, read `skills/koro-operations/SKILL.md`. Its Python CLI performs offline checks only. Run `python -X utf8 -m unittest discover -s tests -p "test_*.py" -v` after changing operations or packaging; use an available Python 3.11+ interpreter. Keep production-target and publishing-account registries separate. Preserve manual ledger fields by stable IDs and distinguish proposed plans, confirmed schedules and verified platform publications.

The plugin uses root `plugin.json` and a repo catalog at `.agents/plugins/marketplace.json`. Source bundles must retain the explicit allowlist in `scripts/bundle.mjs`; never bundle whole local skill folders containing generated path indexes or runtime caches. Do not add local account records, device addresses, customer files or evidence screenshots to public examples.
