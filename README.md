# Real-Time 3D WiFi Radar (Matrix-Style)

This project provides a modular **Python + Three.js** system that scans nearby WiFi APs, computes **Pearson correlation** between RSSI streams, and renders a live 3D cyberpunk graph. The frontend now includes a synthetic preview mode when `/ws` is unavailable.

## Features

- Real-time WiFi scanning (`nmcli` on Linux) with automatic synthetic fallback.
- Sliding-window RSSI history per AP.
- Pearson correlation matrix over AP RSSI vectors.
- Correlation-driven 3D force layout:
  - high correlation attracts
  - weak/negative correlation repels
- Matrix-style 3D scene:
  - glowing AP nodes
  - edge beams for correlated AP pairs
  - fog + grid floor + orbit camera controls
- Interactive controls:
  - toggle SSID labels
  - filter by minimum RSSI
  - band filter (2.4GHz / 5GHz)
  - pause/resume stream
  - click node to inspect metadata and correlation peers

## Architecture

- `backend/wifi_scanner.py`: WiFi scan adapters (real + mock)
- `backend/signal_engine.py`: time-series storage + Pearson correlations
- `backend/layout_engine.py`: incremental 3D force-directed mapping
- `backend/app.py`: FastAPI app + WebSocket snapshot stream
- `frontend/*`: Three.js Matrix-style renderer

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.main
```

Open: <http://localhost:8000>

## Notes

- Linux scanning path uses `nmcli` and maps `SIGNAL%` to an approximate RSSI scale.
- If the backend websocket is unavailable, the frontend auto-falls back to a synthetic demo stream so visual preview still works.
- On unsupported hosts or restricted environments, mock AP streams are emitted so the full visualization pipeline remains testable.
- The design is intentionally modular so Bluetooth/UWB/SDR data sources can be added later by implementing additional scanner adapters.
