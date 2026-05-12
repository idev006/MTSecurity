"""Phase 1 Gate — Unit tests for StateRegistry and camera state machine."""

from __future__ import annotations

import pytest

from ssot.state_registry import CameraState, StateRegistry


def test_initial_camera_state():
    reg = StateRegistry()
    state = reg.get_camera_state(1)
    assert state.state == CameraState.INACTIVE


def test_valid_state_transition():
    reg = StateRegistry()
    reg.get_camera_state(1)   # initialise
    ok = reg.transition_camera(1, CameraState.CONNECTING)
    assert ok is True
    assert reg.get_camera_state(1).state == CameraState.CONNECTING


def test_invalid_state_transition_rejected():
    reg = StateRegistry()
    reg.get_camera_state(1)
    # INACTIVE → ONLINE is not a valid transition
    ok = reg.transition_camera(1, CameraState.ONLINE)
    assert ok is False
    assert reg.get_camera_state(1).state == CameraState.INACTIVE


def test_full_online_path():
    reg = StateRegistry()
    reg.get_camera_state(1)
    assert reg.transition_camera(1, CameraState.CONNECTING)
    assert reg.transition_camera(1, CameraState.ONLINE)
    assert reg.get_camera_state(1).state == CameraState.ONLINE


def test_reconnect_path():
    reg = StateRegistry()
    reg.get_camera_state(1)
    reg.transition_camera(1, CameraState.CONNECTING)
    reg.transition_camera(1, CameraState.ONLINE)
    assert reg.transition_camera(1, CameraState.RECONNECTING)
    assert reg.get_camera_state(1).state == CameraState.RECONNECTING


def test_transition_with_extra_fields():
    reg = StateRegistry()
    reg.get_camera_state(2)
    reg.transition_camera(2, CameraState.CONNECTING)
    reg.transition_camera(2, CameraState.ONLINE, fps=25.0, latency_ms=12.5)
    state = reg.get_camera_state(2)
    assert state.fps == 25.0
    assert state.latency_ms == 12.5


def test_all_camera_states_returns_all():
    reg = StateRegistry()
    reg.get_camera_state(1)
    reg.get_camera_state(2)
    reg.get_camera_state(3)
    all_states = reg.all_camera_states()
    assert len(all_states) == 3


def test_custom_key_value():
    reg = StateRegistry()
    reg.set("last_check", "2026-05-11")
    assert reg.get("last_check") == "2026-05-11"
    assert reg.get("missing", "default") == "default"


def test_system_boot_state():
    reg = StateRegistry()
    reg.set_boot_state("RUNNING")
    assert reg.get_system_state().boot_state == "RUNNING"
