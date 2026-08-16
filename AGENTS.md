# Huckleberry Home Assistant fork

This fork is deliberately read-only. Preserve that boundary in every change.

## Required invariants

- Platforms are limited to `sensor` and `calendar`.
- Never add switches, buttons, services, device actions, or mutation methods.
- Integration code may reach `huckleberry-api` only through `HuckleberryReadOnlyAPI`.
- The facade may expose authentication/token refresh, document reads, history queries, snapshot listeners, and listener cleanup only.
- Pin `huckleberry-api` exactly and update both `manifest.json` and `pyproject.toml` together after auditing the new source.
- Validate every upstream enum, field, and unit against `huckleberry-api`; never guess provider schema values.
- Do not use real household credentials or data in tests, logs, fixtures, screenshots, issues, or commits.

## Validation

Use `uv` for Python commands. Run Ruff, Ty, pytest, HACS validation, and hassfest. Tests must include the read-only contract and at least one failure path. Review the final diff for credential exposure and any Firestore write primitive.

This repository is installed through HACS, so preserve the standard `custom_components/huckleberry` layout and public documentation.
