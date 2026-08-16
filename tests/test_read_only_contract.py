"""Regression tests for the integration's strict read-only boundary."""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from homeassistant.const import Platform

from custom_components.huckleberry.api import HuckleberryReadOnlyAPI
from custom_components.huckleberry.const import PLATFORMS

COMPONENT = Path(__file__).parents[1] / "custom_components" / "huckleberry"
FORBIDDEN_CALL_PREFIXES = (
    "start_",
    "pause_",
    "resume_",
    "cancel_",
    "complete_",
    "log_",
    "create_",
    "update_",
    "delete_",
    "set_",
)
ALLOWED_CLIENT_CALLS = {
    "authenticate",
    "ensure_session",
    "get_child",
    "get_user",
    "list_activity_intervals",
    "list_diaper_intervals",
    "list_feed_intervals",
    "list_health_entries",
    "list_pump_intervals",
    "list_sleep_intervals",
    "setup_activity_listener",
    "setup_child_listener",
    "setup_diaper_listener",
    "setup_feed_listener",
    "setup_health_listener",
    "setup_pump_listener",
    "setup_sleep_listener",
    "stop_all_listeners",
}


def test_only_read_platforms_are_exposed() -> None:
    """The integration must never expose a switch or another control platform."""
    assert PLATFORMS == [Platform.SENSOR, Platform.CALENDAR]
    assert not (COMPONENT / "switch.py").exists()
    assert not (COMPONENT / "services.yaml").exists()


def test_dependency_is_exactly_pinned() -> None:
    """The audited client version must not drift during installation."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["requirements"] == ["huckleberry-api==0.4.3"]


def test_underlying_client_is_only_imported_by_facade() -> None:
    """All application code must cross the capability-limited facade."""
    direct_imports = []
    for source_path in COMPONENT.glob("*.py"):
        if source_path.name == "api.py":
            continue
        if "HuckleberryAPI" in source_path.read_text():
            direct_imports.append(source_path.name)
    assert direct_imports == []


def test_facade_calls_only_audited_client_methods() -> None:
    """Every delegated client call must be an explicit read/auth operation."""
    tree = ast.parse(inspect.getsource(HuckleberryReadOnlyAPI))
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "self"
        and node.func.value.attr == "__client"
    }
    assert calls == ALLOWED_CLIENT_CALLS
    assert not any(call.startswith(FORBIDDEN_CALL_PREFIXES) for call in calls)


def test_integration_has_no_service_registration_or_mutation_calls() -> None:
    """Reject accidental service registration and obvious mutation entry points."""
    offenders: list[str] = []
    for source_path in COMPONENT.glob("*.py"):
        source = source_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            name = node.func.attr
            if name in {"async_register", "register"} or name.startswith(
                FORBIDDEN_CALL_PREFIXES
            ):
                offenders.append(f"{source_path.name}:{node.lineno}:{name}")
    assert offenders == []
