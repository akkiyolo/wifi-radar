from __future__ import annotations

from collections import defaultdict, deque
from math import sqrt
from typing import Dict, List

from .models import APMap, AccessPointSample, AccessPointState, CorrelationMap


class SignalEngine:
    def __init__(self, window_size: int = 40, min_points: int = 8) -> None:
        self.window_size = window_size
        self.min_points = min_points
        self.aps: APMap = {}

    def ingest_batch(self, samples: List[AccessPointSample]) -> None:
        for sample in samples:
            if sample.bssid not in self.aps:
                self.aps[sample.bssid] = AccessPointState(
                    ssid=sample.ssid,
                    bssid=sample.bssid,
                    channel=sample.channel,
                    frequency=sample.frequency,
                    security=sample.security,
                    band=sample.band,
                    rssi_window=deque(maxlen=self.window_size),
                )
            self.aps[sample.bssid].ingest(sample)

    @staticmethod
    def _pearson(x: List[float], y: List[float]) -> float:
        n = len(x)
        if n == 0:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((a - mx) * (b - my) for a, b in zip(x, y))
        den_x = sqrt(sum((a - mx) ** 2 for a in x))
        den_y = sqrt(sum((b - my) ** 2 for b in y))
        den = den_x * den_y
        if den <= 1e-12:
            return 0.0
        return num / den

    def correlation_matrix(self) -> CorrelationMap:
        keys = list(self.aps.keys())
        corr: CorrelationMap = defaultdict(dict)
        for i, a in enumerate(keys):
            corr[a][a] = 1.0
            for j in range(i + 1, len(keys)):
                b = keys[j]
                xa = list(self.aps[a].rssi_window)
                xb = list(self.aps[b].rssi_window)
                n = min(len(xa), len(xb))
                if n < self.min_points:
                    v = 0.0
                else:
                    v = self._pearson(xa[-n:], xb[-n:])
                corr[a][b] = v
                corr[b][a] = v
        return corr

    def to_payload_nodes(self) -> List[Dict]:
        return [
            {
                "id": ap.bssid,
                "ssid": ap.ssid,
                "bssid": ap.bssid,
                "rssi": ap.last_rssi,
                "channel": ap.channel,
                "frequency": ap.frequency,
                "security": ap.security,
                "band": ap.band,
            }
            for ap in self.aps.values()
        ]
