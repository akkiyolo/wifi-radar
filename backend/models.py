from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Deque, Dict, List


@dataclass
class AccessPointSample:
    ssid: str
    bssid: str
    rssi: float
    channel: int | None
    frequency: int | None
    security: str | None
    band: str | None


@dataclass
class AccessPointState:
    ssid: str
    bssid: str
    channel: int | None
    frequency: int | None
    security: str | None
    band: str | None
    rssi_window: Deque[float] = field(default_factory=lambda: deque(maxlen=40))
    last_rssi: float = -100.0

    def ingest(self, sample: AccessPointSample) -> None:
        self.last_rssi = sample.rssi
        self.channel = sample.channel
        self.frequency = sample.frequency
        self.security = sample.security
        self.band = sample.band
        self.rssi_window.append(sample.rssi)


APMap = Dict[str, AccessPointState]
CorrelationMap = Dict[str, Dict[str, float]]
LayoutMap = Dict[str, List[float]]
