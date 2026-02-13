from __future__ import annotations

import random
from typing import Dict, Iterable, List, Tuple

from .models import CorrelationMap, LayoutMap


class ForceLayout3D:
    """Tiny force-directed 3D layout.

    - Positive correlation attracts.
    - Weak/negative correlation repels.
    - Mild origin pull + damping for stability.
    """

    def __init__(self) -> None:
        self.positions: LayoutMap = {}
        self.velocities: LayoutMap = {}

    def ensure_nodes(self, node_ids: Iterable[str]) -> None:
        for n in node_ids:
            if n not in self.positions:
                self.positions[n] = [
                    random.uniform(-8.0, 8.0),
                    random.uniform(-8.0, 8.0),
                    random.uniform(-8.0, 8.0),
                ]
                self.velocities[n] = [0.0, 0.0, 0.0]

    def step(self, corr: CorrelationMap, dt: float = 0.08) -> Tuple[LayoutMap, List[Dict]]:
        ids = list(corr.keys())
        self.ensure_nodes(ids)

        k_attr = 3.5
        k_rep = 1.2
        damping = 0.84
        origin_pull = 0.06

        forces: Dict[str, List[float]] = {n: [0.0, 0.0, 0.0] for n in ids}

        for i, a in enumerate(ids):
            pa = self.positions[a]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                pb = self.positions[b]
                dx, dy, dz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
                dist = (dx * dx + dy * dy + dz * dz) ** 0.5 + 1e-6
                ux, uy, uz = dx / dist, dy / dist, dz / dist

                c = corr[a].get(b, 0.0)
                attraction = max(0.0, c) * k_attr
                repulsion = (1.0 - max(c, 0.0)) * k_rep / (dist * 0.6)
                mag = attraction - repulsion

                fx, fy, fz = ux * mag, uy * mag, uz * mag
                forces[a][0] += fx
                forces[a][1] += fy
                forces[a][2] += fz
                forces[b][0] -= fx
                forces[b][1] -= fy
                forces[b][2] -= fz

        for n in ids:
            p = self.positions[n]
            v = self.velocities[n]
            forces[n][0] += -origin_pull * p[0]
            forces[n][1] += -origin_pull * p[1]
            forces[n][2] += -origin_pull * p[2]

            v[0] = (v[0] + forces[n][0] * dt) * damping
            v[1] = (v[1] + forces[n][1] * dt) * damping
            v[2] = (v[2] + forces[n][2] * dt) * damping

            p[0] += v[0] * dt
            p[1] += v[1] * dt
            p[2] += v[2] * dt

        edges: List[Dict] = []
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                c = corr[a].get(b, 0.0)
                if c > 0.3:
                    edges.append({"source": a, "target": b, "corr": c})

        return self.positions, edges
