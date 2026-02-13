from __future__ import annotations

import asyncio
import random
import re
import shutil
from typing import List

from .models import AccessPointSample


class WifiScanner:
    """Cross-platform-ish scanner with graceful mock fallback.

    Linux: uses nmcli if present.
    Other OS / unavailable tool: emits synthetic APs for visualization/testing.
    """

    def __init__(self, scan_interval_s: float = 1.5) -> None:
        self.scan_interval_s = scan_interval_s
        self._has_nmcli = shutil.which("nmcli") is not None
        self._mock_catalog = [
            ("NEO-MESH", "AA:11:22:33:44:01", 2412, "WPA2"),
            ("ZION-HUB", "AA:11:22:33:44:02", 2437, "WPA2"),
            ("MATRIX-NODE", "AA:11:22:33:44:03", 2462, "WPA3"),
            ("SENTINEL-5G", "AA:11:22:33:44:04", 5180, "WPA2"),
            ("ORACLE-LINK", "AA:11:22:33:44:05", 5200, "OPEN"),
        ]
        self._phase = 0.0

    async def scan(self) -> List[AccessPointSample]:
        if self._has_nmcli:
            samples = await self._scan_nmcli()
            if samples:
                return samples
        return self._scan_mock()

    async def _scan_nmcli(self) -> List[AccessPointSample]:
        cmd = [
            "nmcli",
            "-t",
            "-f",
            "SSID,BSSID,SIGNAL,CHAN,FREQ,SECURITY",
            "dev",
            "wifi",
            "list",
            "--rescan",
            "yes",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                return []
        except Exception:
            return []

        rows = stdout.decode(errors="ignore").splitlines()
        out: List[AccessPointSample] = []
        for row in rows:
            parts = row.split(":")
            if len(parts) < 6:
                continue
            # SSID can contain ':'; BSSID has strict MAC pattern so find it.
            bssid_idx = next(
                (i for i, p in enumerate(parts) if re.fullmatch(r"[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}", p)),
                None,
            )
            if bssid_idx is None or bssid_idx == 0:
                continue
            ssid = ":".join(parts[:bssid_idx]).strip() or "<hidden>"
            bssid = parts[bssid_idx].replace("-", ":").upper()
            tail = parts[bssid_idx + 1 :]
            if len(tail) < 4:
                continue
            try:
                signal_pct = float(tail[0])
                rssi = -100.0 + (signal_pct / 2.0)
                channel = int(tail[1]) if tail[1] else None
                freq = int(tail[2]) if tail[2] else None
            except ValueError:
                continue
            sec = tail[3] if tail[3] else "UNKNOWN"
            band = "5GHz" if (freq or 0) >= 5000 else "2.4GHz"
            out.append(
                AccessPointSample(
                    ssid=ssid,
                    bssid=bssid,
                    rssi=rssi,
                    channel=channel,
                    frequency=freq,
                    security=sec,
                    band=band,
                )
            )
        return out

    def _scan_mock(self) -> List[AccessPointSample]:
        self._phase += 0.3
        out: List[AccessPointSample] = []
        for i, (ssid, bssid, freq, sec) in enumerate(self._mock_catalog):
            wave = 12.0 * (0.6 * __import__("math").sin(self._phase + i * 0.7) + 0.4 * __import__("math").sin(self._phase * 0.5 + i))
            noise = random.uniform(-2.5, 2.5)
            rssi = max(-95.0, min(-30.0, -62.0 + wave + noise))
            out.append(
                AccessPointSample(
                    ssid=ssid,
                    bssid=bssid,
                    rssi=rssi,
                    channel=None,
                    frequency=freq,
                    security=sec,
                    band="5GHz" if freq >= 5000 else "2.4GHz",
                )
            )
        return out
