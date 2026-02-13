from backend.layout_engine import ForceLayout3D
from backend.models import AccessPointSample
from backend.signal_engine import SignalEngine


def test_correlation_detects_similarity():
    engine = SignalEngine(window_size=20, min_points=5)
    for i in range(10):
        a = -60 + i * 0.5
        b = -61 + i * 0.5
        c = -30 - i * 0.5
        engine.ingest_batch(
            [
                AccessPointSample("A", "A", a, None, 2412, "WPA2", "2.4GHz"),
                AccessPointSample("B", "B", b, None, 2417, "WPA2", "2.4GHz"),
                AccessPointSample("C", "C", c, None, 5180, "WPA2", "5GHz"),
            ]
        )
    corr = engine.correlation_matrix()
    assert corr["A"]["B"] > 0.9
    assert corr["A"]["C"] < -0.9


def test_layout_generates_positions_and_edges():
    layout = ForceLayout3D()
    corr = {
        "A": {"A": 1.0, "B": 0.9, "C": 0.0},
        "B": {"A": 0.9, "B": 1.0, "C": 0.1},
        "C": {"A": 0.0, "B": 0.1, "C": 1.0},
    }
    positions, edges = layout.step(corr)
    assert set(positions.keys()) == {"A", "B", "C"}
    assert any(e["source"] in {"A", "B"} and e["target"] in {"A", "B"} for e in edges)
