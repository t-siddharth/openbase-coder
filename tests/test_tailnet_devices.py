from __future__ import annotations

from openbase_coder_cli.services.tailnet_devices import (
    TailnetDevice,
    _devices_from_tailscale_status,
    _url_host_literal,
)


def test_devices_from_tailscale_status_prefers_dns_name() -> None:
    payload = {
        "Self": {
            "HostName": "macbook",
            "DNSName": "macbook.tailnet.ts.net.",
            "TailscaleIPs": ["100.1.1.1"],
            "OS": "macOS",
        },
        "Peer": {
            "node-id": {
                "HostName": "mac-mini",
                "DNSName": "mac-mini.tailnet.ts.net.",
                "TailscaleIPs": ["100.2.2.2"],
                "Online": True,
                "OS": "macOS",
            }
        },
    }

    devices = _devices_from_tailscale_status(payload)

    assert devices == [
        TailnetDevice(
            name="mac-mini",
            host="mac-mini.tailnet.ts.net",
            dns_name="mac-mini.tailnet.ts.net",
            ip="100.2.2.2",
            online=True,
            os="macOS",
        ),
        TailnetDevice(
            name="macbook",
            host="macbook.tailnet.ts.net",
            dns_name="macbook.tailnet.ts.net",
            ip="100.1.1.1",
            online=True,
            os="macOS",
        ),
    ]


def test_url_host_literal_wraps_ipv6() -> None:
    assert _url_host_literal("fd7a:115c:a1e0::1") == "[fd7a:115c:a1e0::1]"
    assert _url_host_literal("device.tailnet.ts.net") == "device.tailnet.ts.net"
