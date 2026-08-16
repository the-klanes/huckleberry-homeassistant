# Huckleberry Read-only for Home Assistant

An unofficial Home Assistant custom integration that consumes Huckleberry baby-care data without exposing any control or write path.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=the-klanes&repository=huckleberry-homeassistant&category=integration)

This fork is based on [Woyken/huckleberry-homeassistant](https://github.com/Woyken/huckleberry-homeassistant) and uses the reverse-engineered `huckleberry-api` client. It is not affiliated with Huckleberry Labs.

## Read-only boundary

- Only `sensor` and `calendar` platforms are loaded.
- There are no switches, buttons, actions, or Home Assistant services.
- A capability-limited facade exposes only authentication, document reads, history queries, subscriptions, and listener cleanup.
- `huckleberry-api` is pinned exactly to `0.4.3`; dependency upgrades require a fresh source audit.
- Contract tests reject mutation calls, service registration, control platforms, or a widened facade.

Huckleberry uses the same Firebase account token for reads and writes, so the provider cannot issue a server-enforced read-only credential. The integration therefore enforces the boundary in its own code and tests. Credentials are stored only in Home Assistant's config entry storage.

## Data exposed

Per child, Home Assistant receives current or latest sleep, nursing, bottle, solids, diaper, potty, growth, medication, temperature, pumping, and activity state. A calendar provides read-only history for sleep, feeding, solids, diaper/potty, health, pumping, and activities.

## Install

1. In HACS, add `https://github.com/the-klanes/huckleberry-homeassistant` as a custom Integration repository.
2. Install **Huckleberry (Read-only)** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and choose Huckleberry.
4. Enter the Huckleberry account email and password.

## Development

```text
uv sync --locked --dev
uv run ruff check .
uv run ty check
uv run pytest
```

The project targets Home Assistant 2026.3+ and Python 3.14.

## License

MIT, retaining the upstream project's license and attribution.
