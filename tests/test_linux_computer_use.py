from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from openbase_coder_cli import linux_computer_use as lcu


@pytest.fixture
def toolchain(monkeypatch):
    monkeypatch.setattr(lcu.shutil, "which", lambda command: f"/usr/bin/{command}")


def test_desktop_maps_remote_control_to_xdotool(toolchain):
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    desktop = lcu.LinuxDesktop(display=":7", runner=fake_run)

    desktop.handle_remote_control_message(
        {"action": "move", "deltaX": 10, "deltaY": -5}
    )
    desktop.handle_remote_control_message({"action": "click", "button": "right"})
    desktop.handle_remote_control_message({"action": "type", "text": "hello"})
    desktop.handle_remote_control_message({"action": "keypress", "keys": ["CTRL", "A"]})
    desktop.handle_remote_control_message({"action": "keypress", "keys": ["COMMAND", "C"]})

    assert commands == [
        ["xdotool", "mousemove_relative", "--", "14", "-7"],
        ["xdotool", "click", "3"],
        ["xdotool", "type", "--clearmodifiers", "--delay", "0", "hello"],
        ["xdotool", "key", "--clearmodifiers", "ctrl+a"],
        ["xdotool", "key", "--clearmodifiers", "ctrl+c"],
    ]


def test_desktop_maps_openai_actions_to_xdotool(toolchain):
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="")

    desktop = lcu.LinuxDesktop(display=":7", runner=fake_run)

    desktop.execute_openai_action(
        {"type": "click", "x": 12.4, "y": 50.2, "button": "left"}
    )
    desktop.execute_openai_action(
        {"type": "drag", "path": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]}
    )

    assert commands == [
        ["xdotool", "mousemove", "12", "50"],
        ["xdotool", "click", "--repeat", "1", "1"],
        ["xdotool", "mousemove", "1", "2"],
        ["xdotool", "mousedown", "1"],
        ["xdotool", "mousemove", "3", "4"],
        ["xdotool", "mouseup", "1"],
    ]


def test_screenshot_rgba_uses_scrot_identify_and_convert(tmp_path, toolchain):
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "scrot":
            Path(command[1]).write_bytes(b"png")
            return subprocess.CompletedProcess(command, 0, stdout="")
        if command[0] == "identify":
            return subprocess.CompletedProcess(command, 0, stdout="10 20")
        if command[0] == "convert":
            return subprocess.CompletedProcess(command, 0, stdout=b"rgba")
        return subprocess.CompletedProcess(command, 0, stdout="")

    desktop = lcu.LinuxDesktop(display=":7", runner=fake_run)

    raw, width, height = desktop.screenshot_rgba()

    assert (raw, width, height) == (b"rgba", 10, 20)
    assert [command[0] for command in commands] == ["scrot", "identify", "convert"]


def test_require_ready_reports_missing_tools(monkeypatch):
    monkeypatch.setattr(lcu.shutil, "which", lambda _command: None)
    desktop = lcu.LinuxDesktop(display="", runner=subprocess.run)

    with pytest.raises(lcu.LinuxComputerUseError) as exc:
        desktop.require_ready()

    assert "DISPLAY" in str(exc.value)
    assert "xdotool" in str(exc.value)
